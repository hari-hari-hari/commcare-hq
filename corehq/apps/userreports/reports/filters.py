from datetime import timedelta

from django.core.urlresolvers import reverse

from sqlagg.filters import (
    BetweenFilter,
    EQFilter,
    GTEFilter,
    GTFilter,
    INFilter,
    ISNULLFilter,
    LTEFilter,
    LTFilter,
    NOTEQFilter,
)

from dimagi.utils.dates import DateSpan


SHOW_ALL_CHOICE = '_all'  # todo: if someone wants to name an actually choice "_all" this will break
NONE_CHOICE = u"\u2400"
CHOICE_DELIMITER = u"\u001f"


class FilterValue(object):

    def __init__(self, filter, value):
        self.filter = filter
        self.value = value

    def to_sql_filter(self):
        raise NotImplementedError()

    def to_sql_values(self):
        raise NotImplementedError()


class DateFilterValue(FilterValue):

    def __init__(self, filter, value):
        assert filter.type == 'date'
        assert isinstance(value, DateSpan) or value is None
        super(DateFilterValue, self).__init__(filter, value)

    def to_sql_filter(self):
        if self.value is None:
            return ""
        return BetweenFilter(self.filter.field, 'startdate', 'enddate')

    def to_sql_values(self):
        if self.value is None:
            return {}

        startdate = self.value.startdate
        enddate = self.value.enddate
        if self.value.inclusive:
            enddate = self.value.enddate + timedelta(days=1) - timedelta.resolution

        if self.filter.compare_as_string:
            startdate = str(startdate)
            enddate = str(enddate)

        return {
            'startdate': startdate,
            'enddate': enddate,
        }


class NumericFilterValue(FilterValue):
    operators_to_filters = {
        '=': EQFilter,
        '!=': NOTEQFilter,
        '>=': GTEFilter,
        '>': GTFilter,
        '<=': LTEFilter,
        '<': LTFilter,
    }

    def __init__(self, filter, value):
        assert filter.type == "numeric"
        assert (isinstance(value, dict) and "operator" in value and "operand" in value) or value is None
        if value:
            assert value['operator'] in self.operators_to_filters
            assert isinstance(value['operand'], int) or isinstance(value['operand'], float)
        super(NumericFilterValue, self).__init__(filter, value)

    def to_sql_filter(self):
        if self.value is None:
            return ""
        filter_class = self.operators_to_filters[self.value['operator']]
        return filter_class(self.filter.field, self.filter.slug)

    def to_sql_values(self):
        if self.value is None:
            return {}
        return {
            self.filter.slug: self.value["operand"],
        }


class ChoiceListFilterValue(FilterValue):

    def __init__(self, filter, value):
        assert filter.type in ('choice_list', 'dynamic_choice_list')
        if not isinstance(value, list):
            # if in single selection mode just force it to a list
            value = [value]
        super(ChoiceListFilterValue, self).__init__(filter, value)

    @property
    def show_all(self):
        return SHOW_ALL_CHOICE in [choice.value for choice in self.value]

    @property
    def is_null(self):
        return NONE_CHOICE in [choice.value for choice in self.value]

    def to_sql_filter(self):
        if self.show_all:
            return ''
        if self.is_null:
            return ISNULLFilter(self.filter.field)
        return INFilter(
            self.filter.field,
            tuple("%s_%d" % (self.filter.slug, i) for i, val in enumerate(self.value))
        )

    def to_sql_values(self):
        if self.show_all or self.is_null:
            return {}
        return {
            "%s_%d" % (self.filter.slug, i): val.value
            for i, val in enumerate(self.value)
        }


def dynamic_choice_list_url(domain, report, filter):
    return reverse('choice_list_api', args=[domain, report.spec._id, filter.name])
