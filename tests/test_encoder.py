import doctest

import jsun


def load_tests(loader, tests, ignore):
    tests.addTests(doctest.DocTestSuite(jsun.encoder))
    return tests
