from StringIO import StringIO
from django.test import TestCase
from django.test.client import Client
from corehq.apps.app_manager.models.common import Application, APP_V1, Module
from corehq.apps.app_manager.success_message import SuccessMessage
from corehq.apps.domain.shortcuts import create_domain
from corehq.apps.users.models import CommCareUser
from datetime import datetime, timedelta
from dimagi.utils.parsing import json_format_datetime
from couchforms.xml import get_simple_response_xml, ResponseNature

submission_template = """<?xml version='1.0' ?>
<data xmlns="%(xmlns)s">
    <meta>
        <username>%(username)s</username>
        <userID>%(userID)s</userID>
    </meta>
</data>
"""


class SuccessMessageTest(TestCase):
    message = "Thanks $first_name ($name)! You have submitted $today forms today and $week forms since Monday."
    domain = "test"
    username = "danny"
    first_name = "Danny"
    last_name = "Roberts"
    password = "123"
    xmlns = "http://dimagi.com/does_not_matter"
    tz = timedelta(hours=0)

    @classmethod
    def setUpClass(cls):
        create_domain(cls.domain)
        couch_user = CommCareUser.create(cls.domain, cls.username, cls.password)
        cls.userID = couch_user.user_id
        couch_user.first_name = cls.first_name
        couch_user.last_name = cls.last_name
        couch_user.save()
        cls.sm = SuccessMessage(cls.message, cls.userID, tz=cls.tz)

        app = Application.new_app(cls.domain, "Test App", application_version=APP_V1)
        app.add_module(Module.new_module("Test Module", "en"))
        form = app.new_form(0, "Test Form", "en")
        form.xmlns = cls.xmlns
        app.success_message = {"en": cls.message}
        app.save()
        # hack: prime the view once so the success message takes even though we use stale queries in submissions
        Application.get_db().view('exports_forms/by_xmlns', limit=1).one()

    def fake_form_submission(self, time=None):
        c = Client()
        submission = submission_template % {
            "userID": self.userID,
            "username": self.username,
            "xmlns": self.xmlns
        }
        f = StringIO(submission.encode('utf-8'))
        f.name = "tempfile.xml"
        kwargs = dict(HTTP_X_SUBMIT_TIME=json_format_datetime(time)) if time else {}
        response = c.post("/a/{self.domain}/receiver/".format(self=self), {
            'xml_submission_file': f,
        }, **kwargs)
        return response

    def test_hours(self):
        self.num_forms_today = 0
        self.num_forms_this_week = 0
        now = datetime.utcnow()
        tznow = now + self.tz
        week_start = tznow - timedelta(days=tznow.weekday())
        week_start = datetime(week_start.year, week_start.month, week_start.day) - self.tz
        day_start = datetime(tznow.year, tznow.month, tznow.day) - self.tz
        spacing = 6
        for h in xrange((24/spacing)*8):
            time = now-timedelta(hours=spacing*h)
            response = self.fake_form_submission(time=time)
            if time > week_start:
                self.num_forms_this_week += 1
            if time > day_start:
                self.num_forms_today += 1
            self.assertEqual(
                response.content,
                get_simple_response_xml((
                    "Thanks {self.first_name} ({self.first_name} {self.last_name})! "
                    "You have submitted {self.num_forms_today} forms today "
                    "and {self.num_forms_this_week} forms since Monday."
                ).format(self=self), nature=ResponseNature.SUBMIT_SUCCESS)
            )
        self.assertEqual(
            self.sm.render(),
            ("Thanks {self.first_name} ({self.first_name} {self.last_name})! "
            "You have submitted {self.num_forms_today} forms today "
            "and {self.num_forms_this_week} forms since Monday.").format(self=self)
        )
