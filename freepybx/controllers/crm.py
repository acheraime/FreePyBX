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
import sys
import md5
import time
import datetime
import shutil
import math
import re
import urllib
import urllib2
import imaplib
import logging
import pprint
import cgi
import cgitb; cgitb.enable()
<<<<<<< HEAD
=======
import transaction
>>>>>>> 210f1b1c21ee3a812f64485cd0f05137c3479af9

import simplejson as json
from simplejson import loads, dumps

from datetime import datetime, date

from pylons import request, response, session, tmpl_context as c, url
from pylons.controllers.util import abort, redirect
from pylons.decorators.rest import restrict
from pylons.decorators import validate
from genshi import HTML

import formencode
from formencode import validators
from decorator import decorator

from webob import Request, Response

from stat import *
from webob import Request, Response

from sqlalchemy import Date, cast, desc, asc
from sqlalchemy.orm import join

from freepybx.model import meta
from freepybx.model.meta import *
from freepybx.model.meta import db
from freepybx.lib.auth import *
from freepybx.lib.forms import *
from freepybx.lib.util import *
from freepybx.lib.util import PbxError, DataInputError, PbxEncoder
from freepybx.lib.base import BaseController, render


logged_in = IsLoggedIn()
log = logging.getLogger(__name__)


class CrmController(BaseController):

    def debug(self, **kw):
        result = []
        environ = request.environ
        keys = environ.keys()
        keys.sort()
        for key in keys:
            result.append("%s: %r"%(key, environ[key]))
        return '<pre>' + '\n'.join(result) + '</pre>'
    
    @authorize(logged_in)
    @jsonify
    def campaigns(self):
        items=[]
        members = []
        try:
            for campaign in CrmCampaign.query.filter(context=session['context']).all():
                for member in CrmGroupMember.query.join(CrmGroup).join(CrmCampaignGroup).filter(CrmCampaignGroup.crm_campaign_id==campaign.id).all():
                    members.append(member.extension)
                items.append({'id': campaign.id, 'name': campaign.name, 'members': ",".join(members)})
                members = []

            db.remove()
            return {'identifier': 'id', 'label': 'name', 'items': items}
        except Exception, e:
            return {'identifier': 'id', 'label': 'name', 'items': items}

    @authorize(logged_in)
    @jsonify
    def campaigns_ids(self):
        names=[]
        ids=[]
        try:
            for row in CrmCampaign.query.filter(context=session['context']).all():
                names.append(row.name)
                ids.append(row.id)
            db.remove()
            return {'names': names, 'ids': ids}

        except Exception, e:
            return {'names': names, 'ids': ids, 'is_error': True, 'message': str(e)}

    @authorize(logged_in)
    def campaign_add(self, **kw):
        schema = CrmCampaignForm()
        try:
            form_result = schema.to_python(request.params)
            crm_campaign = CrmCampaign()
            crm_campaign.name = form_result.get('campaign_name')
            crm_campaign.context = session['context']

            db.add(crm_campaign)
            db.flush()

            crm_group = CrmGroup()
            group.name = form_result.get('campaign_name')
            db.add(crm_group)
            db.flush()

            crm_campaign_group = CrmCampaignGroup()
            crm_campaign_group.name = form_result.get('campaign_name')
            crm_campaign_group.crm_group_id = crm_group.id
            crm_campaign_group.crm_campaign_id = crm_campaign.id
            crm_campaign_group.context = session['context']
            db.add(crm_campaign_group)
            db.flush()

            for extension in form_result.get('campaign_extensions').split(","):
                if not extension.isdigit():
                    continue
                crm_group_member = CrmGroupMember()
                crm_group_member.crm_group_id = crm_group.id
                crm_group_member.context = session['context']
                crm_group_member.extension = extension

                db.add(crm_group_member)
<<<<<<< HEAD
                db.commit()

        except validators.Invalid, error:
            db.rollback()
=======
                transaction.commit()

        except validators.Invalid, error:
            transaction.abort()
>>>>>>> 210f1b1c21ee3a812f64485cd0f05137c3479af9
            return 'Error: %s' % error

        return "Successfully added CRM Campaign."

    @authorize(logged_in)
    def update_campaign_grid(self, **kw):

        w = loads(urllib.unquote_plus(request.params.get("data")))

        try:
            for data in w['modified']:
                crm_campaign_group = CrmCampaignGroup.query.filter(CrmCampaignGroup.crm_campaign_id==data['id'])\
                        .filter(CrmCampaignGroup.context==session['context']).first()
                CrmGroupMember.query.filter(CrmGroupMember.crm_group_id==crm_campaign_group.crm_group_id).delete()

                for member in data['members'].split(","):
                    if not member.strip().isdigit():
                        continue
                    crm_group_member = CrmGroupMember()
                    crm_group_member.crm_group_id = crm_campaign_group.crm_group_id
                    crm_group_member.extension = member.strip()
                    crm_group_member.context = session['context']

                    db.add(crm_group_member)
<<<<<<< HEAD
                    db.commit()
        except:
            db.rollback()
=======
                    transaction.commit()
        except:
            transaction.abort()
>>>>>>> 210f1b1c21ee3a812f64485cd0f05137c3479af9
            return "Error updating campaign."

        return "Successfully updated campaign."

    @authorize(logged_in)
    @jsonify
    def accounts(self):
        items=[]
        try:
            for account in CrmAccount.query.filter(customer_id=session['customer_id']).filter(user_id=session['user_id']).all():
                items.append({'id': account.id, 'name': str(account.first_name)+" "+str(account.last_name), 'address': account.address, \
                              'city': account.city, 'state': account.state, 'zip': account.zip, 'tel': account.tel, 'mobile': account.mobile, \
                              'email': account.email, 'crm_campaign_id': account.crm_campaign_id})

            return response(request.environ, self.start_response)

        except Exception, e:
            return {'identifier': 'id', 'label': 'name', 'items': items}

    
    @authorize(logged_in)
    @jsonify
    def accounts_by_campaign(self, id):
        items=[]
        try:
            for account in CrmAccount.query.join(CrmCampaign).filter(CrmAccount.customer_id==session['customer_id'])\
                        .filter(CrmAccount.user_id==session['user_id']).filter(CrmCampaign.name==id).all():
                items.append({'id': account.id, 'name': str(account.first_name)+" "+str(account.last_name), 'address': account.address, \
                              'city': account.city, 'state': account.state, 'zip': account.zip, 'tel': account.tel, 'mobile': account.mobile, \
                              'email': account.email, 'crm_campaign_id': account.crm_campaign_id})

            return {'identifier': 'id', 'label': 'name', 'items': items}

        except Exception, e:
            return {'identifier': 'id', 'label': 'name', 'items': items, 'is_error': True, 'message': str(e)}

    
    @authorize(logged_in)
    @jsonify
    def account_by_id(self, id):
        items=[]
        try:
            for account in CrmAccount.query.join(CrmCampaign).filter(CrmAccount.customer_id==session['customer_id'])\
                        .filter(CrmAccount.user_id==session['user_id']).filter(CrmCampaign.name==id).all():
                items.append({'id': account.id, 'name': str(account.first_name)+" "+str(account.last_name), 'address': account.address, \
                              'city': account.city, 'state': account.state, 'zip': account.zip, 'tel': account.tel, 'mobile': account.mobile, \
                              'email': account.email, 'crm_campaign_id': account.crm_campaign_id})

            return {'identifier': 'id', 'label': 'name', 'items': items}

        except Exception, e:
            return {'identifier': 'id', 'label': 'name', 'items': items, 'is_error': True, 'message': str(e)}

    @authorize(logged_in)
    def account_add(self, **kw):
        schema = CrmAccountForm()
        try:
            form_result = schema.to_python(request.params)
            crm_account = CrmAccount()
            crm_account.first_name = form_result.get("first_name", "Unknown")
            crm_account.last_name = form_result.get("last_name", "Unknown")
            crm_account.customer = form_result.get("customer")
            crm_account.title = form_result.get("title")
            crm_account.email = form_result.get("email")
            crm_account.address = form_result.get("address")
            crm_account.address_2 = form_result.get("address_2")
            crm_account.city = form_result.get("city")
            crm_account.state = form_result.get("state")
            crm_account.zip = form_result.get("zip")
            crm_account.tel = form_result.get("tel")
            crm_account.tel_ext = form_result.get("tel_ext")
            crm_account.mobile = form_result.get("mobile")
            crm_account.active = True if form_result.get('active')=="true" else False
            crm_account.customer_id = session["customer_id"]
            crm_account.user_id = session["user_id"]
            crm_account.crm_campaign_id = form_result.get("crm_campaign_name")
            crm_account.crm_account_status_type_id = form_result.get("status_type_name")
            crm_account.crm_lead_type_id = form_result.get("crm_lead_type_name")
            
            db.add(crm_account)
<<<<<<< HEAD
            db.commit()

        except validators.Invalid, error:
            db.rollback()
=======
            transaction.commit()

        except validators.Invalid, error:
            transaction.abort()
>>>>>>> 210f1b1c21ee3a812f64485cd0f05137c3479af9
            return 'Error: %s' % error
        
        return "Successfully added CRM account."

    @authorize(logged_in)
    @jsonify
    def account_status_types(self):
        items=[]
        try:
            for ast in CrmAccountStatusType.query.filter(context=session['context']).all():
                items.append({'id': ast.id, 'name': ast.name, 'desc': ast.description})

            return {'identifier': 'id', 'label': 'name', 'items': items}

        except Exception, e:
            return {'identifier': 'id', 'label': 'name', 'items': items, 'is_error': True, 'message': str(e)}

    @authorize(logged_in)
    @jsonify
    def account_lead_types(self):
        items=[]
        try:
            for lead_type in CrmLeadType.query.filter(context=session['context']).all():
                items.append({'id': lead_type.id, 'name': lead_type.name, 'desc': lead_type.description})

            return {'identifier': 'id', 'label': 'name', 'items': items}

        except Exception, e:
            return {'identifier': 'id', 'label': 'name', 'items': items, 'is_error': True, 'message': str(e)}

    @authorize(logged_in)
    @jsonify
    def account_by_id(self, id, **kw):
        items=[]
        try:
            for crm in CrmAccount.query.filter(CrmAccount.customer_id==session['customer_id']).filter(CrmAccount.id==id).all():
                items.append({'id': crm.id, 'first_name': crm.first_name, 'last_name': crm.last_name, 'address': crm.address, 'address_2': crm.address_2,\
                              'city': crm.city, 'state': crm.state, 'zip': crm.zip, 'title': crm.title, 'tel': crm.tel, 'mobile': crm.mobile,\
                              'tel_ext': crm.tel_ext, 'customer': crm.customer, 'email': crm.email, 'url': crm.url, 'crm_account_status_type_id': crm.crm_account_status_type_id,\
                              'crm_lead_type_id': crm.crm_lead_type_id, 'crm_campaign_id': crm.crm_campaign_id, 'created': crm.created.strftime("%m/%d/%Y %I:%M:%S %p"),\
                              'last_modified': crm.last_modified.strftime("%m/%d/%Y %I:%M:%S %p"), 'active': crm.active})

            return {'identifier': 'id', 'label': 'name', 'items': items}

        except Exception, e:
            return {'identifier': 'id', 'label': 'name', 'items': items, 'is_error': True, 'message': str(e)}

    @authorize(logged_in)
    @jsonify
    def account_notes_by_id(self, id, **kw):
        items=[]
        try:
            for note in CrmNote.query.filter(CrmNote.crm_account_id==id).all():
                items.append({'id': note.id, 'created': note.created.strftime("%m/%d/%Y %I:%M:%S %p"),
                              'note': note.note , 'crm_account_id': note.crm_account_id})

            return {'identifier': 'id', 'label': 'name', 'items': items}

        except Exception, e:
            return {'identifier': 'id', 'label': 'name', 'items': items, 'is_error': True, 'message': str(e)}

    @authorize(logged_in)
    def edit_crm_account(self, **kw):
        schema = CrmAccountForm()
        try:
            form_result = schema.to_python(request.params)
            crm_account = CrmAccount.query.filter(id=form_result['id']).filter(customer_id=session['customer_id']).first()
            crm_account.first_name = form_result.get("first_name", "Unknown")
            crm_account.last_name = form_result.get("last_name", "Unknown")
            crm_account.customer = form_result.get("customer")
            crm_account.title = form_result.get("title")
            crm_account.email = form_result.get("email")
            crm_account.address = form_result.get("address")
            crm_account.address_2 = form_result.get("address_2")
            crm_account.city = form_result.get("city")
            crm_account.state = form_result.get("state")
            crm_account.zip = form_result.get("zip")
            crm_account.tel = form_result.get("tel")
            crm_account.tel_ext = form_result.get("tel_ext")
            crm_account.mobile = form_result.get("mobile")
            crm_account.active = True if form_result.get('active')=="true" else False
            crm_account.customer_id = session["customer_id"]
            crm_account.user_id = session["user_id"]
            crm_account.crm_campaign_id = form_result.get("crm_campaign_name")
            crm_account.crm_account_status_type_id = form_result.get("status_type_name")
            crm_account.crm_lead_type_id = form_result.get("crm_lead_type_name")
            
            db.add(crm_account)
<<<<<<< HEAD
            db.commit()
=======
            transaction.commit()
>>>>>>> 210f1b1c21ee3a812f64485cd0f05137c3479af9

        except validators.Invalid, error:
             return 'Error: %s' % error
        
        return "Successfully edited CRM account."     

    @authorize(logged_in)
    def add_crm_account_note(self, **kw):
        try:
            crm_note = CrmNote()
            crm_note.note = request.params.get('crm_note')
            crm_note.crm_account_id = request.params.get('crm_acct_id')
            crm_note.created = datetime.now()

            db.add(crm_note)
<<<<<<< HEAD
            db.commit()

        except validators.Invalid, error:
            db.rollback()
=======
            transaction.commit()

        except validators.Invalid, error:
            transaction.abort()
>>>>>>> 210f1b1c21ee3a812f64485cd0f05137c3479af9
            return 'Error: %s' % error

        return "Successfully added CRM notes."
                   
    
    