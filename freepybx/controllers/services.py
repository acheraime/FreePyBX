"""
    This Source Code Form is subject to the terms of the Mozilla Public
    License, v. 2.0. If a copy of the MPL was not distributed with this
    file, You can obtain one at http://mozilla.org/MPL/2.0/.

    Software distributed under the License is distributed on an "AS IS"
    basis, WITHOUT WARRANTY OF ANY KIND, either express or implied. See the
    License for the specific language governing rights and limitations
    under the License.

    The Original Code is FreePyBX/VoiceWARE.

    The Initial Developer of the Original Code is Noel Morgan,
    Copyright (c) 2011-2012 VoiceWARE Communications, Inc. All Rights Reserved.

    http://www.vwci.com/

    You may not remove or alter the substance of any license notices (including
    copyright notices, patent notices, disclaimers of warranty, or limitations
    of liability) contained within the Source Code Form of the Covered Software,
    except that You may alter any license notices to the extent required to
    remedy known factual inaccuracies.
"""
import os
import cgitb; cgitb.enable()
import urllib
import logging

import simplejson as json
from simplejson import loads, dumps

from pylons import request, response, session, tmpl_context as c, url
from pylons.controllers.util import abort, redirect
from pylons import config
from pylons.decorators.rest import restrict
from pylons.decorators import validate, jsonify

import formencode
from formencode import validators
from decorator import decorator

from genshi import HTML

import formencode
from formencode import validators

from freepybx.lib.base import BaseController, render
from freepybx.model import meta
from freepybx.model.meta import *
from freepybx.model.meta import db
from freepybx.lib.pymap.imap import Pymap
from freepybx.lib.auth import *
from freepybx.lib.forms import *
from freepybx.lib.util import *
from freepybx.lib.util import PbxError, DataInputError, PbxEncoder
from freepybx.lib.validators import *

logged_in = IsLoggedIn()
super_user = IsSuperUser()
credentials = HasCredential(object)
log = logging.getLogger(__name__)

fs_vm_dir = config['app_conf']['fs_vm_dir']
fs_profile = config['app_conf']['fs_profile']


class CredentialError(Exception):
    message=""

    def __init__(self, message=None):
        Exception.__init__(self, message or self.message)

class ServicesController(BaseController):
    """ Services Controller """

    def index(self, **kw):
        return "Nothing"

    @authorize(super_user)
    def service_grid(self, **kw):
        return render("services/service_list.html")

    @authorize(super_user)
    def service_plan_grid(self, **kw):
        return render("services/service_plans.html")

    @authorize(super_user)
    def voip_profile_grid(self, **kw):
        return render("services/voip_profiles.html")

    @authorize(super_user)
    def voip_policy_grid(self, **kw):
        return render("services/voip_policies.html")

    @authorize(super_user)
    def service_add(self, **kw):
        return render("services/service_add.html")

    @authorize(super_user)
    @jsonify
    def billing_service_types(self):
        items=[]
        try:
            for billing_servicde_type in BillingServiceType.query.all():
                items.append({'id': billing_servicde_type.id,
                              'name': billing_servicde_type.name,
                              'description': billing_servicde_type.description})

            db.remove()
            return {'identifier': 'id', 'label': 'name', 'items': items}
        except Exception, e:
            return {'identifier': 'id', 'label': 'name', 'items': items, 'is_error': True, 'message': str(e)}

    @authorize(super_user)
    @jsonify
    def services(self):
        items=[]
        try:
            for service in BillingService.query.all():
                items.append({'id': service.id, 'name': service.name,
                              'description': service.description,
                              'billing_service_type_id': service.billing_service_type_id,
                              'service_id': service.service_id})

            db.remove()
            return {'identifier': 'id', 'label': 'name', 'items': items}

        except Exception, e:
            return {'identifier': 'id', 'label': 'name', 'items': items, 'is_error': True, 'message': str(e)}


    @authorize(super_user)
    @jsonify
    def service_plans(self):
        items=[]
        try:
            for service in BillingService.query.all():
                items.append({'id': service.id, 'name': service.name,
                              'description': service.description,
                              'billing_service_type_id': service.billing_service_type_id,
                              'service_id': service.service_id})

            db.remove()
            return {'identifier': 'id', 'label': 'name', 'items': items}

        except Exception, e:
            return {'identifier': 'id', 'label': 'name', 'items': items, 'is_error': True, 'message': str(e)}
