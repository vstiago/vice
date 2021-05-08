import pytest

from ..assembly import compile_code, parse_used_labels, \
    trim_comment, \
    map_assembly_lines, LabelFilter


def test_compile_code_no_extension():
    assembly_code = compile_code('no_extension', ['void foo() { return; }'])
    assert len(assembly_code) == 0


def test_compile_code_no_extension_with_language():
    assembly_code = compile_code('no_extension', ['void foo() { return; }'],
                                 parameters='-x c')
    assert len(assembly_code) != 0


def test_compile_code_invalid_compiler():
    assembly_code = compile_code('foo.cc', ['void foo() { return; }'],
                                 compiler='invalid_compiler')
    assert len(assembly_code) == 0


def test_compile_code_invalid_syntax():
    assembly_code = compile_code('foo.cc', ['void foo() { return; }'],
                                 syntax='invalid_syntax')
    assert len(assembly_code) == 0


def test_compile_code_no_syntax():
    assembly_code = compile_code('foo.cc', ['void foo() { return; }'],
                                 syntax='')
    assert len(assembly_code) != 0

    
def test_compile_code_failed_to_compile():
    assembly_code = compile_code('foo.cc', ['void foo() { return; '])
    assert len(assembly_code) == 0


def test_compile_code():
    assembly_code = compile_code('foo.cc', ['void foo() { return; }'])
    assert len(assembly_code) != 0


def test_parse_used_labels():
    assembly_lines = ['.LC0:', '.L3:', 'je .L4', '.L4:',
                      'mov rax, rbx', 'jne .L3', 'lea rdi, .LC0[rip]']
    used_labels = parse_used_labels(assembly_lines)
    assert used_labels == {'.LC0', '.L3', '.L4'}


def test_parse_used_labels_mangled():
    assembly_lines = ['_Z3fooi:']
    used_labels = parse_used_labels(assembly_lines)
    assert used_labels == {'foo(int)'}


def test_parse_used_labels_no_label():
    assembly_lines = ['.LC0:', '.L3:', '.L4:',
                      'mov rax, rbx']
    used_labels = parse_used_labels(assembly_lines)
    assert used_labels == set()


def test_parse_used_labels_commented_label():
    assembly_lines = ['.L3:',  '# jne .L3']
    used_labels = parse_used_labels(assembly_lines)
    assert used_labels == set()


def test_trim_comment():
    assert trim_comment("mv rax, 1 # a = 1") == "mv rax, 1"
    assert trim_comment("# full comment line") == ""
    assert trim_comment("") == ""


def test_map_assembly_lines():
    assembly_code = """
_Z3addii:
.LFB0:
	.file 1 "simple.cc"
	.loc 1 1 23
	pushq   %rbp
	.cfi_def_cfa_offset 16
	movq    %rsp, %rbp
	.loc 1 2 13
	movl    -4(%rbp), %edx
"""

    result = map_assembly_lines(assembly_code.split('\n'))
    expected = [('add(int, int):', 0),
                ('.LFB0:', 0),
                ('\t.file 1 "simple.cc"', 0),
                ('\t.loc 1 1 23', 0),
                ('\tpushq   %rbp', 1),
                ('\t.cfi_def_cfa_offset 16', 0),
                ('\tmovq    %rsp, %rbp', 1),
                ('\t.loc 1 2 13', 0),
                ('\tmovl    -4(%rbp), %edx', 2)]

    assert len(result) == len(expected)
    for i in range(len(expected)):
        assert result[i] == expected[i]


def test_map_assembly_lines_ignored_lines():
    assembly_code = """
	.file 1 "simple.cc"
	.loc 1 1 23

.starting_with_dot
	.starting_with_tab_dot
# comment
1:
_Z3addii:
	# other comment
"""
    result = map_assembly_lines(assembly_code.split('\n'))
    for line, number in result:
        if number != 0:
            pytest.fail(f'{line}: number {number} expected 0')


def test_label_filter():
    used_labels = {'.LC0', '.L3'}
    label_filter = LabelFilter(used_labels)
    assert label_filter(('  mov rax, rbx', 1))
    assert not label_filter(('', 0))
    assert label_filter(('', 1))
    assert label_filter(('.LC0:', 0))
    assert label_filter(('\t.ascii\t"Hello"', 0))
    assert not label_filter(('\t.loc 1 2 3', 0))
    assert not label_filter(('\t.ascii\t"World"', 0))
    assert label_filter(('.L3:', 0))
    assert not label_filter(('.LC1:', 0))
