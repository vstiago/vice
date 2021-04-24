import os
import re
import subprocess
import tempfile
from enum import Enum
from typing import List, Set, Tuple

import cxxfilt
import vim

window_map = {}


class WindowType(Enum):
    SOURCE = 0
    DESTINATION = 1


class ViceWindow:
    def __init__(self, window, window_type, tmp_file):
        self.window = window
        self.buffer = window.buffer
        self.window_type = window_type
        self.line_map = []
        self.tmp_file = tmp_file
        self.mirror = None
        self.update_scheduled = False


class ViceSrcWindow(ViceWindow):
    def __init__(self, window, tmp_file):
        super().__init__(self, window, WindowType.Source, tmp_file)
        self.mirrors = {}


def create_destination_window():
    tmp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.s', prefix='vice')
    splitright = vim.options['splitright']
    if splitright:
        vim.command(f'vnew {tmp_file.name}')
    else:
        vim.options['splitright'] = True
        vim.command(f'vnew {tmp_file.name}')
        vim.options['splitright'] = False

    vim.command('set tabstop=8')
    # vim.options['tabstop'] = 8

    dst_buffer = vim.current.buffer
    # print('bufhidden', dst_buffer.options['bufhidden'])
    # dst_buffer.options['bufhidden'] = 'do_something'
    dst_buffer.options['buftype'] = 'nofile'

    return ViceWindow(vim.current.window, WindowType.DESTINATION, tmp_file)


def get_windows(cur_buffer):
    cur_window = window_map.get(cur_buffer)
    if cur_window is None:
        return None

    if cur_window.window_type == WindowType.DESTINATION:
        # print('valid', dst_buffer.valid)
        # print('buflisted', dst_buffer.options['buflisted'])
        # print('bufhidden', dst_buffer.options['bufhidden'])
        # print('in ', dst_buffer in vim.buffers)
        # if dst_buffer.valid or dst_buffer.options['buflisted']:
        #     return cur_buffer, dst_buffer
        return cur_window.mirror, cur_window

    if cur_window.mirror is None:
        return None

    return cur_window, cur_window.mirror


def get_or_create_windows(cur_buffer):
    windows = get_windows(cur_buffer)
    if windows is not None:
        return windows

    src_window = window_map[vim.current.buffer]
    dst_window = create_destination_window()

    src_window.mirror = dst_window
    dst_window.mirror = src_window

    # window_map[src_window.buffer] = src_window
    window_map[dst_window.buffer] = dst_window

    return src_window, dst_window


def assembly(vim_buffer, compiler: str, parameters: str, syntax: str):
    splitted_path = os.path.splitext(vim_buffer.name)
    current_extension = splitted_path[1] if len(splitted_path) > 1 else None

    tmp_file = tempfile.NamedTemporaryFile(mode='w',
                                           suffix=current_extension,
                                           prefix='vice',
                                           delete=False)
    for line in vim_buffer:
        print(line, file=tmp_file)
    tmp_file.close()

    cur_window = window_map.get(vim_buffer)
    if cur_window is None:
        cur_window = ViceWindow(vim.current.window, WindowType.SOURCE, tmp_file)
        window_map[vim_buffer] = cur_window
    else:
        cur_window.tmp_file = tmp_file

    cmd = [compiler, tmp_file.name, '-g1', '-masm='+syntax, '-S',
           '-o', '-']
    cmd += filter(None, parameters.split(' '))
    # print(cmd)
    try:
        code_ass = subprocess.check_output(cmd)
    except subprocess.CalledProcessError as err:
        print('Failed to compile.', err)
        return
    return str(code_ass, 'ascii').splitlines()


def trim_comment(line):
    output = line.split('#')[0]
    return output.rstrip()


def parse_used_labels(lines: List[str]) -> Set[str]:
    used_labels = set()
    re_label = re.compile('(\.[A-Za-z0-9_\.]+)')

    for line in lines:
        if line == '' or line[0] == '#' or line[0] == '.' or \
                line[-1] == ':' or line.startswith('\t.'):
            continue

        label = re_label.search(line)
        if label:
            # print(line)
            # print(label)
            used_labels.add(label.group())

    # print(used_labels)
    return used_labels


def parse_assembly(lines: List[str]) -> List[Tuple[str, int]]:
    used_labels = parse_used_labels(lines)

    other_labels = {'.ascii', '.asciz', '.string', '.float', '.single',
                    '.double', '.quad', '.octa', '.long'}
    valid_label = False
    location_marker = f'\t.loc'
    assembly_lines = []
    source_line = 0

    for line in lines:
        if line == '':
            valid_label = False
            source_line = 0
            continue

        if line[0] == '.':
            if line[:-1] in used_labels:
                assembly_lines.append((line, 0))
                valid_label = True
            continue

        if line.startswith('\t.'):
            tokens = line.split('\t')
            if valid_label and tokens[1] in other_labels:
                assembly_lines.append((line, 0))
            else:
                valid_label = False

            if line.startswith(location_marker):
                tokens = line.replace('\t', ' ').split(' ')
                # print(tokens)
                source_line = int(tokens[3])
            continue

        valid_label = False

        if line.startswith('#'):
            continue

        if line[:-1].isnumeric():
            continue

        if line[0] == '_':
            func_name = line.split(':')[0]
            demangled_name = cxxfilt.demangle(func_name)
            assembly_lines.append((demangled_name + ':', 0))
            source_line = 0
            continue

        line = trim_comment(line)
        if line == '':
            continue

        assembly_lines.append((line, source_line))

    return assembly_lines


def view_assembly(compiler='gcc', parameters='', syntax='intel'):
    if vim.current.buffer.name.endswith('.s'):
        return

    assembly_code = assembly(vim.current.buffer, compiler, parameters, syntax)
    if assembly_code is None:
        return

    src_window, dst_window = get_or_create_windows(vim.current.buffer)

    parsed_assembly_lines = parse_assembly(assembly_code)
    # print(parsed_assembly_lines)
    
    assembly_lines = []

    src_window.line_map = [0] * (len(src_window.buffer[:]) + 1)
    dst_window.line_map = [0]  # [0] * (len(parsed_assembly_lines) + 1)
    for text, line_number in parsed_assembly_lines:
        assembly_lines.append(text)
        dst_window.line_map.append(line_number)
        if line_number != 0 and src_window.line_map[line_number] == 0:
            src_window.line_map[line_number] = len(assembly_lines)

    # print(src_window.line_map)
    # print(dst_window.line_map)

    clear_lines()
    dst_window.buffer.options['readonly'] = False
    dst_window.buffer[:] = assembly_lines
    dst_window.buffer.options['readonly'] = True
    add_lines((src_window, dst_window))

    vim.current.window = src_window.window
    # vim.current.buffer = src_window.buffer
    # 'CursorMoved'
    # au[tocmd] [group] {event} {pat} [nested] {cmd}
    # vim.command('augroup vice')
    # vim.command('autocmd CursorMoved vice*.s call ViceCursorMoved()')


def schedule_update():
    # print('schedule_update')
    cur_window = window_map.get(vim.current.buffer)
    if cur_window is None or cur_window.window_type == WindowType.DESTINATION:
        vim.command('autocmd! ViceOnChange')

    if cur_window.update_scheduled:
        return
    cur_window.update_scheduled = True
    vim.command("let bla = timer_start(1000, 'ViceUpdateAssembly')")


def update_assembly():
    # print('update_assembly')
    cur_window = window_map.get(vim.current.buffer)
    cur_window.update_scheduled = False
    view_assembly()


def cursor_moved():
    cur_window = window_map.get(vim.current.buffer)
    if cur_window is None:
        return

    dst_window = cur_window.mirror
    dst_line = cur_window.line_map[cur_window.window.cursor[0]]

    if dst_line == 0:
        return

    dst_column = dst_window.window.cursor[1]
    dst_window.window.cursor = (dst_line, dst_column)
    vim.command('redraw!')


place_id = 1


def add_sign(sign_id: int, file_name: str, line: int):
    global place_id
    cmd = f'sign place {place_id} line={line} name=vice_sign_{sign_id} group=vice file={file_name}'
    # print(cmd)
    vim.command(cmd)
    place_id += 1


def add_lines(windows=None):
    if windows is None:
        windows = get_windows(vim.current.buffer)
        if windows is None:
            return

    src_window, dst_window = windows
    line_signs = []
    sign_id = 1
    sign_max = 16
    # print(src_window.line_map)
    # print(dst_window.line_map)
    for line_number, dst_line in enumerate(src_window.line_map):
        if dst_line == 0:
            line_signs.append(0)
            continue
        add_sign(sign_id, src_window.buffer.name, line_number)
        line_signs.append(sign_id)
        sign_id += 1
        if sign_id > sign_max:
            sign_id = 1

    # print(line_signs)
    for line_number, src_line in enumerate(dst_window.line_map):
        if src_line == 0:
            continue
        sign_id = line_signs[src_line]
        add_sign(sign_id, dst_window.buffer.name, line_number)

    src_window.lines_enabled = True


def sign_unplace(buffer_name: str):
    vim.command(f'sign unplace * group=vice file={buffer_name}')


def clear_lines(clean_mirror=True):
    cur_buffer = vim.current.buffer
    sign_unplace(cur_buffer.name)

    if clean_mirror:
        cur_window = window_map.get(cur_buffer)
        if cur_window is None:
            return
        mirror = cur_window.mirror
        sign_unplace(mirror.buffer.name)

        cur_window.lines_enabled = False


def toggle_lines(windows=None):
    if windows is None:
        windows = get_windows(vim.current.buffer)
        if windows is None:
            return

    src_window, dst_window = windows

    if src_window.lines_enabled:
        clear_lines()
    else:
        add_lines(windows)

