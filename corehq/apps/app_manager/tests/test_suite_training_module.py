from __future__ import absolute_import
from __future__ import unicode_literals

from django.test import SimpleTestCase

from corehq.apps.app_manager.models import Application, TrainingModule
from corehq.apps.app_manager.tests.util import TestXmlMixin


class TrainingModuleSuiteTest(SimpleTestCase, TestXmlMixin):

    def test_training_module(self):
        app = Application.new_app('domain', 'Untitled Application')
        training_module = TrainingModule.new_module('training module', None)
        training_module.put_in_root = True
        app.add_module(training_module)
        app.new_form(training_module.id, "Untitled Form", None)
        self.assertXmlPartialEqual(
            """
            <partial>
                <menu root="training-root" id="m0">
                    <text>
                        <locale id="modules.m0"/>
                    </text>
                    <command id="m0-f0"/>
                </menu>
                <menu id="training-root">
                    <text>
                        <locale id="training.root.title"/>
                    </text>
                </menu>
            </partial>
            """,
            app.create_suite(),
            "./menu"
        )