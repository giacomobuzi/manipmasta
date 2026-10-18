import math

import pytest

from app import protocol as P


@pytest.mark.parametrize("line,expected", [
    ("ping", "PING"),
    ("  home ", "HOME"),
    ("enable 1", "ENABLE 1"),
    ("jog x -10.5", "JOG X -10.5"),
    ("JOG G 0.1", "JOG G 0.1"),
    ("move x 100 f 50", "MOVE X 100 F 50"),
    ("MOVE X -20", "MOVE X -20"),
    ("gap 12.5", "GAP 12.5"),
    ("run", "RUN"),
    ("run g0=40 cx=0", "RUN cx=0 g0=40"),
    ("set x_vmax 120", "SET x_vmax 120"),
    ("SET IP 192.168.50.61", "SET ip 192.168.50.61"),
    ("get od", "GET od"),
    ("save", "SAVE"), ("defaults", "DEFAULTS"), ("stop", "STOP"),
])
def test_validate_ok(line, expected):
    assert P.validate_command(line) == expected


@pytest.mark.parametrize("line", [
    "", "   ", "FOO", "REBOOT", "HOME 1", "ENABLE 2", "JOG Y 10", "JOG X abc", "MOVE G 10",
    "MOVE X 10 F", "MOVE X 10 F -5", "GAP", "RUN zz=3", "RUN g0", "RUN g0=4 g0=5", "RUN g0=abc",
    "SET foo 1", "SET ip 300.1.1.1", "SET mqtt_port 99999", "SET x_spm abc", "GET",
    "PING\nHOME", "SET mqtt_pass a b", "x" * 201,
])
def test_validate_rejects(line):
    with pytest.raises(P.CommandError):
        P.validate_command(line)


def test_parse_run_line_spec_example():
    line = "RUN cx=0 s0=150 s1=300 g0=40 g1=5 dg=3 f=60 n=2 od=2"
    args = P.parse_run_args(line.split()[1:])
    assert args == {"cx": 0, "s0": 150, "s1": 300, "g0": 40, "g1": 5, "dg": 3, "f": 60, "n": 2, "od": 2}
    assert isinstance(args["n"], int)
    assert P.build_run_line(args) == line
    assert P.validate_command(line.lower()) == line


def test_run_defaults_fill_missing():
    p = P.run_params(P.parse_run_args(["g0=30"]))
    assert p["g0"] == 30 and p["g1"] == 5 and p["n"] == 2


def test_build_run_line_decimals():
    p = dict(P.RUN_DEFAULTS, g1=2.5, od=1.25, dg=0.5)
    line = P.build_run_line(p)
    assert "g1=2.5" in line and "od=1.25" in line and "dg=0.5" in line
    assert P.parse_run_args(line.split()[1:])["g1"] == 2.5


@pytest.mark.parametrize("g0,g1,dg,n,exp", [
    (40, 5, 3, 2, 14),     # ceil(35/3)=12 + 2
    (30, 3, 2, 3, 17),     # ceil(13.5)=14 + 3
    (45, 8, 4, 1, 11),     # ceil(9.25)=10 + 1
    (10, 4, 2, 0, 3),      # divisione esatta
    (5, 5, 1, 2, 2),       # già al gap finale
    (0.9, 0.6, 0.1, 0, 3), # niente errori di arrotondamento
])
def test_num_passes(g0, g1, dg, n, exp):
    assert P.num_passes(g0, g1, dg, n) == exp


def test_pass_plan_follows_spec():
    p = P.run_params({})
    plan = P.pass_plan(p)
    assert len(plan) == P.num_passes(40, 5, 3, 2)
    assert plan[0][0] == 40 and plan[0][1] == 37          # avanti a g0, indietro a g0-dg
    assert plan[0][2] == 150 and plan[-1][2] == 300       # s interpolata s0 -> s1
    assert all(b == max(5, a - 3) for a, b, _ in plan)
    # ultime n passate tutte a g1
    assert plan[-1][:2] == (5, 5) and plan[-2][:2] == (5, 5)
    assert min(g for a, b, _ in plan for g in (a, b)) == 5


def test_estimate_reasonable():
    p = P.run_params({})
    t = P.estimate_seconds(p)
    # 14 passate doppie di ~2x(2s+120) mm a 60 mm/s: fra 4 e 7 minuti
    assert 240 < t < 420


def test_limits():
    assert P.run_limits_error(P.run_params({})) is None
    assert "X" in P.run_limits_error(P.run_params({"cx": 500}))
    assert P.run_limits_error(P.run_params({"g0": 4, "g1": 5}))
    assert P.run_limits_error(P.run_params({"f": 500}))
    assert P.run_limits_error(P.run_params({"g1": 0.1}))
