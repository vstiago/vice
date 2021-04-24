import os
import re
import subprocess
import tempfile
from typing import List, Set, Tuple

import cxxfilt


def assembly(source_name: str, source_lines: List[str], compiler: str,
             parameters: str, syntax: str):
    split_path = os.path.splitext(source_name)
    current_extension = split_path[1] if len(split_path) > 1 else None

    tmp_file = tempfile.NamedTemporaryFile(mode='w',
                                           suffix=current_extension,
                                           prefix='vice',
                                           delete=False)
    for line in source_lines:
        print(line, file=tmp_file)
    tmp_file.close()

    cmd = [compiler, tmp_file.name, '-g1', '-masm=' + syntax, '-S',
           '-o', '-']
    cmd += filter(None, parameters.split(' '))
    # print(cmd)
    try:
        code_ass = subprocess.check_output(cmd)
    except subprocess.CalledProcessError as err:
        print('Failed to compile.', err)
        return None, None

    return tmp_file, str(code_ass, 'ascii').splitlines()


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
            used_labels.add(label.group())

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
