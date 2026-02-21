from pipeline.analysis.analyzers.html import HTMLAnalyzer
from pipeline.analysis.analyzers.js import JSAnalyzer
from pathlib import Path


def test_html_analyzer_basic(tmp_path):
    f = tmp_path / "a.html"
    f.write_text('<div ng-repeat="x in xs" ng-click="do()"></div>')

    a = HTMLAnalyzer()
    rm, rt, re, rd, rh = a.analyze([f])

    assert len(rt) == 1
    assert rt[0].loops
    assert rt[0].events


def test_js_analyzer_invalid_js_does_not_crash(tmp_path):
    f = tmp_path / "a.js"
    f.write_text("this is not valid js")

    a = JSAnalyzer()
    rm, rt, re, rd, rh = a.analyze([f])

    assert rm == []
    assert rd == []
