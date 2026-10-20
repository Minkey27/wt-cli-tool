from wt.app import _usage_cells

MIB = 1024**2


def test_usage_cells_sum_the_stack():
    cpu, mem = _usage_cells([(56.6, 1500 * MIB), (24.0, 146 * MIB), (0.1, 7 * MIB)])
    assert (cpu.plain, mem.plain) == ("81%", "1.6G")


def test_usage_cells_show_megabytes_below_one_gigabyte():
    _, mem = _usage_cells([(0.0, 515 * MIB)])
    assert mem.plain == "515M"


def test_usage_cells_are_dashes_when_nothing_runs():
    cpu, mem = _usage_cells([])
    assert (cpu.plain, cpu.style, mem.plain) == ("—", "dim", "—")
