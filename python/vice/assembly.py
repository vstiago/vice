import os
import re
import subprocess
import tempfile
from typing import Iterator, List, Set, Tuple

import cxxfilt


def compile_code(source_name: str, source_lines: List[str],
                 compiler: str = 'gcc', parameters: str = '',
                 syntax: str = 'intel') -> List[str]:
    split_path = os.path.splitext(source_name)
    current_extension = split_path[1] if len(split_path) > 1 else None

    tmp_file = tempfile.NamedTemporaryFile(mode='w',
                                           suffix=current_extension,
                                           prefix='vice',
                                           delete=False)
    for line in source_lines:
        print(line, file=tmp_file)
    tmp_file.close()

    cmd = [compiler, '-g1', '-S', '-o', '-']
    cmd += filter(None, parameters.split(' '))
    if len(syntax) != 0:
        cmd += ['-masm=' + syntax]
    cmd += [tmp_file.name]

    # print(cmd)
    try:
        result = subprocess.check_output(cmd)
    except subprocess.CalledProcessError as err:
        print('Failed to compile.', err)
        return []
    except FileNotFoundError as err:
        print('File not found.', err)
        return []

    return str(result, 'ascii').splitlines()


def parse_used_labels(lines: List[str]) -> Set[str]:
    used_labels = set()
    re_label = re.compile('\\.[A-Za-z0-9_.]+')

    for line in lines:
        if line == '' or line[0] == '#' or line[0] == '.' or \
                line.startswith('\t.'):
            continue

        if line[0] == '_':
            func_name = line.split(':')[0]
            demangled_name = cxxfilt.demangle(func_name)
            line = demangled_name + ':'
            used_labels.add(demangled_name)
            continue

        label = re_label.search(line)
        if label:
            used_labels.add(label.group())

    return used_labels


def trim_comment(line, comment_marker='#'):
    output = line.split(comment_marker)[0]
    return output.rstrip()


def map_assembly_lines(lines: List[str], location_marker='\t.loc') -> \
        List[Tuple[str, int]]:
    result = []
    source_line = 0

    for line in lines:
        if line == '':
            source_line = 0
            continue

        if line[0] == '.':
            result.append((line, 0))
            continue

        if line.startswith('\t.'):
            result.append((line, 0))

            if line.startswith(location_marker):
                tokens = line.replace('\t', ' ').split(' ')
                # print(tokens)
                source_line = int(tokens[3])
            continue

        if line.startswith('#') or line[:-1].isnumeric():
            continue

        if line[0] == '_':
            func_name = line.split(':')[0]
            demangled_name = cxxfilt.demangle(func_name)
            result.append((demangled_name + ':', 0))
            source_line = 0
            continue

        line = trim_comment(line)
        if line == '':
            continue

        result.append((line, source_line))

    return result


class LabelFilter:
    other_labels = {'.ascii', '.asciz', '.string', '.float', '.single',
                    '.double', '.quad', '.octa', '.long'}

    def __init__(self, used_labels):
        self.used_labels = used_labels
        self.valid_label = False

    def __call__(self, line_number: Tuple[str, int]) -> bool:
        if line_number[1] != 0:
            return True
        line = line_number[0]
        if line == '':
            self.valid_label = False
            return False

        # if line[0] == '.':
        if line[:-1] in self.used_labels:
            self.valid_label = True
            return True

        if line.startswith('\t.'):
            tokens = line.split('\t')
            if self.valid_label and tokens[1] in LabelFilter.other_labels:
                return True

        self.valid_label = False

        return False


def parse_assembly(lines: List[str]) -> Iterator[Tuple[str, int]]:
    used_labels = parse_used_labels(lines)

    mapped_lines = map_assembly_lines(lines)

    return filter(LabelFilter(used_labels), mapped_lines)
