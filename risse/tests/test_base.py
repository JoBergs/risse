#encoding: utf-8
from unittest import TestCase

from ..spiders.base import *

class BaseClassTestCase(TestCase):
    def test_find_date_range_year(self):
        self.base = RisseSpider("testpath", "Dortmund", None, None, None, "False")
        assert self.base.get_dates("2011", None) == ('01.01.2011', '31.12.2011')

    def test_find_date_range_long_month(self):
        self.base = RisseSpider("testpath", "Dortmund", None, None, None, "False")
        assert self.base.get_dates("2011", "1") == ('01.01.2011', '31.01.2011')

    def test_find_date_range_normal_month(self):
        self.base = RisseSpider("testpath", "Dortmund", None, None, None, "False")
        assert self.base.get_dates("2011", "4") == ('01.04.2011', '30.04.2011')

    def test_find_date_range_september(self):
        self.base = RisseSpider("testpath", "Dortmund", None, None, None, "False")
        assert self.base.get_dates("2011", "9") == ('01.09.2011', '30.09.2011')

    def test_find_date_range_february(self):
        self.base = RisseSpider("testpath", "Dortmund", None, None, None, "False")
        assert self.base.get_dates("2011", "2") == ('01.02.2011', '28.02.2011')

    def test_find_date_range_february_leap(self):
        self.base = RisseSpider("testpath", "Dortmund", None, None, None, "False")
        assert self.base.get_dates("2016", "2") == ('01.02.2016', '29.02.2016')