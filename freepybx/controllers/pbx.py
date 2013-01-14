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
import re
import datetime
import time
import shutil
import cgi
import cgitb
import csv
import urllib
import logging

import simplejson as json
from simplejson import loads, dumps

import formencode
from formencode import validators

from datetime import datetime
from decorator import decorator

from pylons import request, response, session, tmpl_context as c, url
from pylons import config
from pylons.controllers.util import abort, redirect
from pylons.decorators.rest import restrict
from pylons.decorators import validate, jsonify

from freepybx.lib.base import BaseController, render
from freepybx.model import meta
from freepybx.model.meta import *
from freepybx.model.meta import Session as db
from freepybx.lib.pymap.imap import Pymap
from freepybx.lib.auth import *
from freepybx.lib.forms import *
from freepybx.lib.util import *
from freepybx.lib.validators import *

from genshi import HTML
from subprocess import call
from stat import *

from sqlalchemy import Date, cast, desc, asc
from sqlalchemy.orm import join

try:
    cgitb.enable()
except:
    pass
try:
    from ESL import *
except:
    pass

logged_in = IsLoggedIn()
credential = HasCredential
log = logging.getLogger(__name__)
DEBUG=False

fs_vm_dir = config['app_conf']['fs_vm_dir']
fs_dir = config['app_conf']['fs_dir']
ESL_HOST = config['app_conf']['esl_host']
ESL_PORT = config['app_conf']['esl_port']
ESL_PASS = config['app_conf']['esl_pass']


class PbxController(BaseController):
    """ This is the main controller for the config of the pbx. FreeSWITCH
        makes requests from the curl xml interface when the configuration
        is requested from FreeSWITCH."""

    def index(self):
        return "<Nothing/>"

    def sofiaconf(self):
        c.domains = []
        c.odbc_credentials = config['app_conf']['odbc_credentials']
        c.pbx_profiles = PbxProfile.query.all()
        c.pbx_gateways = PbxGateway.query.all()
        c.pbx_acl_blacklist = PbxAclBlacklist.query.all()
        for domain in PbxContext.query.filter_by(profile=c.pbx_profiles[0].name).all():
            c.domains.append(domain.domain)

        return render('xml/sofia.conf.xml')

    def switchconf(self):
        c.odbc_credentials = config['app_conf']['odbc_credentials']
        return render('xml/switch.conf.xml')

    def aclconf(self):
        c.pbx_gateways = PbxGateway.query.all()
        c.pbx_acl_blacklist = PbxAclBlacklist.query.all()
        c.odbc_credentials = config['app_conf']['odbc_credentials']
        return render('xml/switch.conf.xml')

    def callcenterconf(self):
        c.odbc_credentials = config['app_conf']['odbc_credentials']
        c.domains = []
        c.call_center_queues = []
        c.call_center_agents = []
        c.call_center_tiers = []

        try:
            for domain in PbxContext.query.distinct(PbxContext.domain).all():
                c.domains.append(domain.domain)

            for context in PbxContext.query.distinct(PbxContext.context):
                for queue in CallCenterQueue.query.filter_by(context=context.context).all():
                    c.call_center_queues.append(
                            {'name': queue.name, 'domain': queue.domain, 'moh_sound': queue.moh_sound.split(",")[1],
                             'time_base_score': queue.time_base_score,
                             'max_wait_time': queue.max_wait_time,
                             'max_wait_time_with_no_agent': queue.max_wait_time_with_no_agent,
                             'max_wait_time_with_no_agent_reached': queue.max_wait_time_with_no_agent_reached,
                             'tier_rules_apply': queue.tier_rules_apply,
                             'tier_rule_wait_second': queue.tier_rule_wait_second,
                             'tier_rule_wait_multiply_level': queue.tier_rule_wait_multiply_level,
                             'record_calls': queue.record_calls,
                             'tier_rule_agent_no_wait': queue.tier_rule_agent_no_wait,
                             'discard_abandoned_after': queue.discard_abandoned_after,
                             'abandoned_resume_allowed': queue.abandoned_resume_allowed, 'strategy': queue.strategy,
                             'announce_sound': queue.announce_sound,
                             'announce_frequency': queue.announce_frequency})
                    for agent in CallCenterAgent.query.filter_by(context=context.context).all():
                        c.call_center_agents.append({'name': agent.name, 'domain': queue.domain, 'type': agent.type,
                                                     'max_no_answer': agent.max_no_answer, 'extension': agent.extension,
                                                     'wrap_up_time': agent.wrap_up_time,
                                                     'reject_delay_time': agent.reject_delay_time,
                                                     'busy_delay_time': agent.busy_delay_time,
                                                     'timeout': agent.timeout})
                    for tier in CallCenterTier.query.all():
                        c.call_center_tiers.append({'agent': tier.agent, 'domain': queue.domain, 'queue': tier.queue,
                                                    'level': tier.level, 'position': tier.position})
        except:
            return render('xml/notfound.xml')

        return render('xml/callcenter.conf.xml')

    def cdr_pg_csvconf(self):
        return render('xml/cdr_pg_csv.conf.xml')

    def dbconf(self):
        c.odbc_credentials = config['app_conf']['odbc_credentials']
        return render('xml/db.conf.xml')

    def faxconf(self):
        return render('xml/fax.conf.xml')

    def fifoconf(self):
        c.domains=[]
        for domain in PbxContext.query.distinct(PbxContext.domain).all():
            c.domains.append(domain.domain)
        c.odbc_credentials = config['app_conf']['odbc_credentials']
        return render('xml/fifo.conf.xml')

    def presence_mapconf(self):
        c.domains = []
        for domain in PbxContext.query.filter_by(profile=c.pbx_profiles[0].name).all():
            c.domains.append(domain.domain)
        return render('xml/presence_map.conf.xml')

    def voicemailconf(self):
        c.odbc_credentials = config['app_conf']['odbc_credentials']
        c.pbx_profiles = PbxProfile.query.all()
        return render('xml/voicemail.conf.xml')

    def lcrconf(self):
        c.odbc_credentials = config['app_conf']['odbc_credentials']
        c.pbx_profiles = PbxProfile.query.all()
        return render('xml/lcr.conf.xml')

    def configuration(self, **kw):
        conf = re.sub('[^A-Za-z0-9]+', '', request.params.get('key_value', "Nothing"))

        if has_method(self, conf):
            return getattr(self, conf)()
        else:
            return render('xml/notfound.xml')

    def directory(self, **kw):
        """ The directory method is called when FreeSWITCH needs information
            about the users endpoints and for things like gateways for the 
            profile, group pointers, as well as our custom stuff like virtual
            mailbox extensions. All specific to XML. Needed for registrations 
            and XML. """

        try:
            if request.params.has_key('purpose'):
                if request.params["purpose"] == "gateways":
                    gateway = db.execute("SELECT pbx_gateways.* FROM pbx_gateways "
                                         "INNER JOIN pbx_profiles "
                                         "ON pbx_profiles.id = pbx_gateways.pbx_profile_id "
                                         "WHERE pbx_profiles.name = :profile_name",
                                         {'profile_name': str(request.params["profile"])})
                    c.gateway = {'name': str(request.params["profile"]), 'gateway': gateway}
                    db.remove()
                    return render('xml/gateways.xml')

            domain = request.params.get('domain', None)

            if not db.query(Customer.active).join(PbxContext).filter(PbxContext.domain==domain).filter(Customer.active==True).first():
                return render('xml/notfound.xml')

            c.groups = []
            c.voicemailboxes = []

            for group in PbxGroup.query.filter_by(context=domain).all():
                exts = []
                for ext in PbxGroupMember.query.filter_by(pbx_group_id=group.id).all():
                    exts.append({'ext': ext.extension})
                c.groups.append({'name': group.name, 'extensions': exts})

            for vmext in PbxVirtualMailbox.query.filter_by(context=domain).all():
                c.voicemailboxes.append({'extension': vmext.extension, 'vm_password': vmext.vm_password,
                                         'vm_attach_email': vmext.vm_attach_email, 'vm_save': vmext.vm_save,
                                         'vm_notify_email': vmext.vm_notify_email, 'vm_email': vmext.vm_email})

            if not request.params.has_key('user'):
                c.endpoints = []
                c.domain = domain
                c.endpoints = PbxEndpoint.query.filter_by(user_context = domain).all()

                return render('xml/directory.xml')
            else:
                user = request.params.get('user')
                c.domain = domain
                c.endpoints = PbxEndpoint.query.filter_by(user_context = domain).filter_by(auth_id=user).all()

                if not len(c.endpoints):
                    for vmext in PbxVirtualMailbox.query.filter_by(context=domain).all():
                        c.voicemailboxes.append({'extension': vmext.extension, 'vm_password': vmext.vm_password,
                                                 'vm_attach_email': vmext.vm_attach_email, 'vm_save': vmext.vm_save,
                                                 'vm_notify_email': vmext.vm_notify_email, 'vm_email': vmext.vm_email})
                    if c.voicemailboxes:
                        return render('xml/virtual_mailboxes.xml')
                    else:
                        return render('xml/notfound.xml')

                return render('xml/directory.xml')
        except:
            return render('xml/notfound.xml')
        finally:
            db.remove()

    def dialplan(self, **kw):
        """ This is a recursion engine that creates several objects of nested
            dictionaries and arrays and that are subsequently passed into the
            template context of pylons and interpolated into the xml template
            stream by genshi to create XML dynamically for FreeSWITCH.

            We create this for call control as well as use lua for setting
            inbound routes by context from the default context, since we are
            using only one profile for all sip traffic. Both the XML and lua
            call control are needed. It helps you be lazy and hardcode trash
            into the dialplan that you will eventually forget about.

            :param c.profile: request parameter posted from FreeSWITCH
            :type c.profile: type description

            :returns context object
            :rtype: serialized Dict

            :returns dids object
            :rtype: serialized Dict

            Renders:  ``xml/dialplan.xml``

            I'll highlight the important stuff.

            Pull all of the dids from the db to setup call control for lua
            from the default context on incoming calls from outside the switch.

            Iterate over the contexts and create objects for the xml stream engine.
            These objects are passed to dialplan.xml in the templates/xml directory.

            Retrieve all of the routes.

            Only concerned with what is needed for transfers to the xml context.

            More to do in xml with virtual extensions for things like continue on fail
            timeouts to local voicemail boxes.

            After we check and make sure that our route object is iterable,
            we grab the conditions and actions for the route. We have a template
            meta class and default set of conditions/actions for orphaned routes.
            Not really needed, but it will help you when you make mistakes your
            users will still get dialplan.

            Retrieve the route conditions and actions for the conditions.

            Serialize into context template and pass objects to xml rendering stream.
        """

        c.contexts = []
        routes =  []
        conditions = []
        actions = []

        c.profile = request.params.get('variable_sofia_profile_name','default')

        try:
            c.dids = PbxDid.query.join(Customer).filter(Customer.active==True).filter(PbxDid.active==True).all()
            for context in PbxContext.query.join(Customer).filter(Customer.active==True).distinct(PbxContext.context):
                conference_bridges = PbxConferenceBridge.query.filter_by(context=context.context).all()
                voicemailboxes = PbxVirtualMailbox.query.filter_by(context=context.context).all()
                faxes = PbxFax.query.filter_by(context=context.context).all()
                gateway = PbxGateway.query.join(PbxProfile).filter(PbxProfile.name==c.profile).first()

                for route in PbxRoute.query.filter_by(context=context.context).all():
                    ep = None
                    if route.pbx_route_type_id not in range(1,3):
                        continue
                    if route.pbx_route_type_id == 2:
                        continue
                    route_conditions = is_iter_obj(PbxCondition.query.filter_by(pbx_route_id=route.id).all())
                    if route.pbx_route_type_id == 1:
                        ep = PbxEndpoint.query.filter_by(id=route.pbx_to_id).first()
                        user = User.query.filter_by(id=ep.user_id).first()
                        rec = ep.record_inbound_calls
                    else:
                        rec = None
                    if route_conditions is not None:
                        for condition in route_conditions:
                            for action in PbxAction.query.filter_by(pbx_condition_id=condition.id).order_by(PbxAction.precedence).all():
                                actions.append({'application': action.application, 'data': action.data})
                            ds = get_findme(route.name, context.context)
                            if len(ds):
                                actions.append({'application': "set", 'data': "ignore_early_media=true"})
                            for d in ds:
                                actions.append({'application': "set", 'data': "call_timeout="+str(ep.call_timeout)})
                                actions.append({'application': "bridge", 'data': d})
                            conditions.append({'field': condition.field, 'expression': condition.expression, 'actions': actions})
                            actions  = []
                    else:
                        for action in PbxActionTmpl.query.join(PbxConditionTmpl).filter(PbxConditionTmpl.pbx_route_type_id==route.pbx_route_type_id).order_by(PbxActionTmpl.precedence).all():
                            actions.append({'application': action.application, 'data': action.data})

                        actions.append({'application': "bridge", 'data': "sofia/"+str(get_profile())+"/$1"+"%"+context.context})
                        conditions.append({'field': "destination_number", 'expression': "^("+route.name+")", 'actions': actions})
                        actions  = []

                    routes.append({'name': route.name, 'continue_route': str(route.continue_route).lower(), 'conditions': conditions, 'user_id': user.id, 'customer_id': user.customer_id,
                                   'voicemail_enabled': str(route.voicemail_enabled).lower(), 'voicemail_ext': route.voicemail_ext, 'record_inbound_calls': rec})
                    conditions = []

                c.contexts.append({'domain': context.domain, 'context': context.context, 'routes': routes, 'effective_caller_id_name': context.caller_id_name,
                                   'effective_caller_id_number': context.caller_id_number, 'origination_caller_id_name': context.caller_id_name,
                                   'origination_caller_id_number': context.caller_id_number, 'gateway': gateway.name, 'conference_bridges': conference_bridges,
                                   'voicemailboxes': voicemailboxes, 'faxes': faxes, 'recordings_dir': fs_vm_dir+context.domain+"/recordings/"})

                routes = []
            db.remove()
            return render('xml/dialplan.xml')

        except Exception, e:
            return render('xml/notfound.xml')

        finally:
            db.remove()

    @authorize(logged_in)
    @jsonify
    def users(self):
        items=[]

        try:
            for row in User.query.filter(User.customer_id==session['customer_id']).order_by(asc(User.id)).all():
                exts = []
                for ext in PbxEndpoint.query.filter(PbxEndpoint.user_id==row.id).filter_by(user_context=session['context']).all():
                    exts.append(ext.auth_id)
                if not len(exts) > 0:
                    extension = "No Extension"
                else:
                    extension = ",".join(exts)

                items.append({'id': row.id, 'extension': extension, 'username': row.username, 'password': row.password, 'first_name': row.first_name, 'name': row.first_name +' '+row.last_name,
                              'last_name': row.last_name, 'address': row.address, 'address_2': row.address_2, 'city': row.city, 'state': row.state, 'zip': row.zip,
                              'tel': row.tel, 'mobile': row.mobile, 'notes': row.notes, 'created': row.created.strftime("%m/%d/%Y %I:%M:%S %p"), 'updated': row.updated.strftime("%m/%d/%Y %I:%M:%S %p"), 'active': row.active,
                              'group_id': row.group_id, 'last_login': row.last_login.strftime("%m/%d/%Y %I:%M:%S %p"), 'remote_addr': row.remote_addr, 'session_id': row.session_id, 'customer_id': row.customer_id})
            db.remove()
            return {'identifier': 'id', 'label': 'name', 'items': items}

        except KeyError, e:
            return {'identifier': 'id', 'label': 'name', 'items': [], 'is_error': True, 'message': 'Exception: key_error: '+ str(e)}

        except Exception, e:
            return {'identifier': 'id', 'label': 'name', 'items': [], 'is_error': True, 'message': 'Exception: ' + str(e)}

    @authorize(logged_in)
    @jsonify
    def user_by_id(self, id, **kw):
        items=[]

        try:
            for row in User.query.filter(User.customer_id==session['customer_id'])\
                                        .filter(User.id==id).order_by(asc(User.id)).all():
                exts = []
                for ext in PbxEndpoint.query.filter(PbxEndpoint.user_id==row.id).all():
                    exts.append(ext.auth_id)
                if not len(exts) > 0:
                    extension = "No Extension"
                else:
                    extension = ",".join(exts)
                items.append({'id': row.id, 'extension': extension, 'username': row.username, 'password': row.password, 'first_name': row.first_name, 'portal_extension': row.portal_extension,
                              'last_name': row.last_name, 'address': row.address, 'address_2': row.address_2, 'city': row.city, 'state': row.state, 'zip': row.zip,
                              'tel': row.tel, 'mobile': row.mobile, 'notes': row.notes, 'created': row.created.strftime("%m/%d/%Y %I:%M:%S %p"), 'updated': row.updated.strftime("%m/%d/%Y %I:%M:%S %p"), 'active': row.active,
                              'group_id': row.group_id, 'last_login': row.last_login.strftime("%m/%d/%Y %I:%M:%S %p"), 'remote_addr': row.remote_addr, 'session_id': row.session_id, 'customer_id': row.customer_id})
            db.remove()
            return {'identifier': 'id', 'label': 'name', 'items': items}

        except KeyError, e:
            return {'identifier': 'id', 'label': 'name', 'items': [], 'is_error': True, 'message': 'Exception: key_error: '+ str(e)}

        except Exception, e:
            return {'identifier': 'id', 'label': 'name', 'items': [], 'is_error': True, 'message': 'Exception: ' + str(e)}

    @restrict("POST")
    @authorize(logged_in)
    def add_user(self, **kw):
        schema = UserForm()
        try:
            form_result = schema.to_python(request.params)
            user = User()
            user.username = form_result.get("username")
            user.password = form_result.get("password")
            user.first_name = form_result.get("first_name")
            user.last_name = form_result.get("last_name")
            user.address = form_result.get("address")
            user.address_2 = form_result.get("address_2")
            user.city = form_result.get("city")
            user.state = form_result.get("state")
            user.zip = form_result.get("zip")
            user.tel = form_result.get("tel")
            user.mobile = form_result.get("mobile")
            user.active = form_result.get("active")
            user.customer_id = session["customer_id"]
            user.notes = form_result.get("notes")
            user.portal_extension = form_result.get("extension")

            db.add(user)

            group = Group.query.filter(Group.id==form_result.get("group_id", 2)).first()
            group.users.append(user)
            db.add(group)

            db.flush()
            db.commit()

            context = PbxContext.query.filter(PbxContext.customer_id==session['customer_id']).first()

            email = EmailAccount()
            endpoint = PbxEndpoint()
            route = PbxRoute()
            condition = PbxCondition()
            action = PbxAction()

            if(session['has_crm']):
                if len(form_result.get("email"))>0 and len(form_result.get("email_password"))>0 and len(form_result.get("email_server"))>0:
                    email = EmailAccount()
                    email.user_id = user.id
                    email.customer_id = session['customer_id']
                    email.email = form_result.get("email")
                    email.password = form_result.get("email_password")
                    email.mail_server = form_result.get("email_server")
                    email = form_result.get("email", None)

                    db.add(email)
                    db.commit()
                    db.flush()
            else:
                email = None

            if request.params.has_key('extension'):
                extension = form_result.get("extension").strip()
                if extension.isdigit():
                    if (len(get_extensions(ext))>0):
                        raise Exception("Extension already exists!")
                        ext_failed = True
                    else:
                        ext_failed = False
                else:
                    ext_failed = True
            else:
                ext_failed = True

            if not ext_failed:
                endpoint = PbxEndpoint()
                endpoint.auth_id = form_result.get("extension")
                endpoint.password = form_result.get("extension_password")
                endpoint.outbound_caller_id_name = context.caller_id_name
                endpoint.outbound_caller_id_number = context.caller_id_number
                endpoint.internal_caller_id_name = user.name
                endpoint.internal_caller_id_number = form_result.get("extension")
                endpoint.user_context = context.context
                endpoint.force_transfer_context = context.context
                endpoint.user_originated = u'true'
                endpoint.toll_allow = u'domestic'
                endpoint.call_timeout = form_result.get("call_timeout", 20)
                endpoint.accountcode = context.caller_id_number
                endpoint.pbx_force_contact = form_result.get("pbx_force_contact", u'nat-connectile-dysfunction')
                endpoint.vm_email = form_result.get("vm_email")
                endpoint.vm_password = form_result.get("vm_password")
                endpoint.vm_attach_email = True if form_result.get("vm_email", None) is not None else False
                endpoint.vm_delete = False
                endpoint.user_id = user.id

                db.add(endpoint)
                db.flush()
                db.commit()

                route = PbxRoute()
                route.context = context.context
                route.domain = context.context
                route.name = form_result.get("extension")
                route.continue_route = True
                route.voicemail_enable = True
                route.voicemail_ext = form_result.get("extension")
                route.pbx_route_type_id = 1
                route.pbx_to_id = endpoint.id

                db.add(route)
                db.commit(); db.flush()

                condition = PbxCondition()
                condition.context = context.context
                condition.domain = context.context
                condition.field = u'destination_number'
                condition.expression = u'^('+form_result.get("extension")+')$'
                condition.pbx_route_id = route.id

                db.add(condition)
                db.commit(); db.flush()

                action = PbxAction()
                action.pbx_condition_id = con.id
                action.context = context.context
                action.domain = context.context
                action.precedence = 1
                action.application = u'set'
                action.data = u'hangup_after_bridge=true'

                db.add(action)
                db.commit(); db.flush()

                action = PbxAction()
                action.pbx_condition_id = con.id
                action.context = context.context
                action.domain = context.context
                action.precedence = 2
                action.application = u'set'
                action.data = u'call_timeout=20'

                db.add(s)
                db.commit(); db.flush()

                action = PbxAction()
                action.pbx_condition_id = condition.id
                action.context = context.context
                action.domain = context.context
                action.precedence = 3
                action.application = u'bridge'
                action.data = u'{force_transfer_context='+context.context+'}sofia/'+str(get_profile())+'/'+form_result.get("extension")+'%'+context.context

                db.add(action)
                db.flush()
                db.commit()

        except validators.Invalid, error:
            db.remove()
            return 'Validation Error: %s' % error

        db.remove()
        return "Sucessfully added user."

    @restrict("POST")
    @authorize(logged_in)
    def edit_user(self, **kw):
        schema = UserEditForm()
        try:
            form_result = schema.to_python(request.params)
            user = User.query.filter(User.id==form_result.get("id"))\
                                .filter(User.customer_id==session['customer_id']).first()
            if form_result.get("username") != user.username:
                if not get_usernames(str(form_result.get("username", None))):
                    user.username = form_result.get("username")

            user.password = form_result.get("password")
            user.first_name = form_result.get("first_name")
            user.last_name = form_result.get("last_name")
            user.address = form_result.get("address")
            user.address_2 = form_result.get("address_2")
            user.city = form_result.get("city")
            user.state = form_result.get("state")
            user.zip = form_result.get("zip")
            user.tel = form_result.get("tel")
            user.mobile = form_result.get("mobile")
            user.portal_extension = form_result.get('extension', 0)
            user.active = True if form_result.get("active", None) is not None else False
            user.customer_id = session["customer_id"]
            user.notes = form_result.get("notes")
            db.commit(); db.flush()

            db.execute("UPDATE user_groups SET group_id = :group_id where user_id = :user_id",\
                    {'group_id': form_result.get('group_id', 3) , 'user_id': u.id})

            db.flush()
            db.commit()
            db.remove()

        except validators.Invalid, e:
            return 'Error updating user: %s' % e

        return "User successfully updated."

    @authorize(logged_in)
    def update_users_grid(self, **kw):

        try:

            w = loads(urllib.unquote_plus(request.params.get("data")))

            for i in w['modified']:
                user = User.query.filter_by(customer_id=session['customer_id'])\
                                .filter_by(id=i['id']).first()
                user.first_name = i['first_name']
                user.last_name = i['last_name']
                user.username = i['username']
                user.password = i['password']

                db.flush()
                db.commit()
                db.remove()

            return "Successfully updated users."
        except Exception, e:
            return "Error: %s" % e

    @restrict("GET")
    @authorize(logged_in)
    def del_user(self, **kw):

        u = User.query.filter(User.id==request.params['id']).filter(User.customer_id==session['customer_id']).first()
        delete_extension_by_user_id(u.id)

        try:
            id = request.params['id']
            if not id.isdigit():
                raise Exception("YOUR IP: "+str(request.params["HTTP_REMOTE_DUDE"])+" INFO WAS SENT TO THE ADMIN FOR BLOCKING.")
            User.query.filter(User.id==id).filter(User.customer_id==session['customer_id']).delete()
            db.commit(); db.flush()
        except:
            db.remove()
            return "Error deleting user."

        db.remove()
        return  "Successfully deleted user."

    @authorize(logged_in)
    @jsonify
    def extensions(self):
        items=[]
        try:
            for endpoint in PbxEndpoint.query.filter(PbxEndpoint.user_context==session['context']).all():
                ep_stats = []
                for pbx_reg in PbxRegistration.query.filter(PbxRegistration.sip_realm==session['context']).filter(PbxRegistration.sip_user==endpoint.auth_id).all():
                    ep_stats.append({'ip': pbx_reg.network_ip, 'port': pbx_reg.network_port})
                is_online = True if len(ep_stats) > 0 else False
                if is_online:
                    ip = ep_stats[0]["ip"]
                    port = ep_stats[0]["port"]
                else:
                    ip = "Unregistered"
                    port = "N/A"

                for user in User.query.filter_by(id=endpoint.user_id).all():
                    items.append({'id': endpoint.id, 'name': str(user.first_name)+' '+str(user.last_name), 'extension': endpoint.auth_id, 'password': endpoint.password,
                                  'outbound_caller_id_name': endpoint.outbound_caller_id_name, 'outbound_caller_id_number': endpoint.outbound_caller_id_number,
                                  'internal_caller_id_name': endpoint.internal_caller_id_name, 'internal_caller_id_number': endpoint.internal_caller_id_number,
                                  'vm_email': endpoint.vm_email, 'vm_password': endpoint.vm_password, 'vm_save': endpoint.vm_save,'vm_attach_email': endpoint.vm_attach_email,
                                  'vm_notify_email': endpoint.vm_notify_email, 'mac': endpoint.mac, 'device_type_id': endpoint.device_type_id,
                                  'transfer_fallback_extension': endpoint.transfer_fallback_extension, 'is_online': is_online, 'ip': ip, 'port': port,
                                  'auto_provision': endpoint.auto_provision})

            db.remove()
            return {'identifier': 'extension', 'label': 'name', 'items': items}

        except KeyError, e:
            db.remove()
            return {'identifier': 'id', 'label': 'name', 'items': [], 'is_error': True, 'message': 'KeyError: ' + str(e)}

        except Exception, e:
            db.remove()
            return {'identifier': 'id', 'label': 'name', 'items': [], 'is_error': True, 'message': 'Exception: ' + str(e)}

    @authorize(logged_in)
    @jsonify
    def extension_by_id(self, id, **kw):
        items=[]

        try:
            for endpoint in PbxEndpoint.query.filter(PbxEndpoint.user_context==session['context']).filter(PbxEndpoint.id==id).all():
                for user in User.query.filter_by(id=endpoint.user_id).all():
                    items.append({'id': endpoint.id, 'name': str(user.first_name)+' '+str(user.last_name), 'extension': endpoint.auth_id, 'password': endpoint.password,
                                  'outbound_caller_id_name': endpoint.outbound_caller_id_name, 'outbound_caller_id_number': endpoint.outbound_caller_id_number,
                                  'internal_caller_id_name': endpoint.internal_caller_id_name, 'internal_caller_id_number': endpoint.internal_caller_id_number,
                                  'vm_email': endpoint.vm_email, 'vm_password': endpoint.vm_password, 'vm_attach_email': endpoint.vm_attach_email, 'vm_save': endpoint.vm_save,
                                  'vm_notify_email': endpoint.vm_notify_email, 'calling_rule_id': endpoint.calling_rule_id,
                                  'transfer_fallback_extension': endpoint.transfer_fallback_extension, 'find_me': endpoint.find_me, 'follow_me_1': endpoint.follow_me_1,
                                  'follow_me_2': endpoint.follow_me_2, 'follow_me_3': endpoint.follow_me_3, 'follow_me_4': endpoint.follow_me_4, 'call_timeout': endpoint.call_timeout,
                                  'timeout_destination': endpoint.timeout_destination, 'record_inbound_calls': endpoint.record_inbound_calls, 'record_outbound_calls': endpoint.record_outbound_calls,
                                  'mac': endpoint.mac, 'device_type_id': endpoint.device_type_id, 'auto_provision': endpoint.auto_provision, 'include_xml_directory': endpoint.include_xml_directory})
            db.remove()
            return {'identifier': 'extension', 'label': 'name', 'items': items}

        except KeyError, e:
            db.remove()
            return {'identifier': 'id', 'label': 'name', 'items': [], 'is_error': True, 'message': 'KeyError: ' + str(e)}

        except Exception, e:
            db.remove()
            return {'identifier': 'id', 'label': 'name', 'items': [], 'is_error': True, 'message': 'Exception: ' + str(e)}

    @authorize(logged_in)
    def add_extension(self):
        schema = ExtensionForm()
        customer = Customer.query.filter(Customer.id==session['customer_id']).first()

        if customer.max_extensions >= PbxEndpoint.query.filter(Customer.id==session['customer_id']).count():
            return "Sorry, so have reached your maximum extension limit. Please contact customer service."

        try:
            form_result = schema.to_python(request.params)
            endpoint = PbxEndpoint()
            endpoint.auth_id = form_result.get('extension')
            endpoint.password = form_result.get('password')
            endpoint.outbound_caller_id_name = form_result.get('outbound_caller_id_name')
            endpoint.outbound_caller_id_number = form_result.get('outbound_caller_id_number')
            endpoint.internal_caller_id_name = form_result.get('internal_caller_id_name')
            endpoint.internal_caller_id_number = form_result.get('internal_caller_id_number')
            endpoint.vm_email = form_result.get('vm_email')
            endpoint.vm_password = form_result.get('vm_password')
            endpoint.vm_attach_email = form_result.get('vm_attach_email')
            endpoint.vm_notify_email = form_result.get('vm_notify_email')
            endpoint.vm_save = form_result.get('vm_save')
            endpoint.transfer_fallback_extension = form_result.get('transfer_fallback_extension')
            endpoint.accountcode = customer.tel
            endpoint.follow_me_1 = form_result.get('follow_me_1')
            endpoint.follow_me_2 = form_result.get('follow_me_2')
            endpoint.follow_me_3 = form_result.get('follow_me_3')
            endpoint.follow_me_4 = form_result.get('follow_me_4')
            endpoint.call_timeout = form_result.get('call_timeout', 20)
            time_dest = form_result.get('timeout_destination')
            endpoint.timeout_destination = time_dest if time_dest.isdigit() else None
            endpoint.record_inbound_calls = form_result.get('record_inbound_calls', False)
            endpoint.record_outbound_calls = form_result.get('record_outbound_calls', False)
            endpoint.user_id = int(session['user_id'])
            endpoint.user_context = session['context']
            endpoint.force_transfer_context = session['context']
            endpoint.user_originated = u'true'
            endpoint.toll_allow = u'domestic'
            endpoint.accountcode = customer.tel
            calling_rule_id = form_result.get('calling_rule_id')
            endpoint.calling_rule_id = calling_rule_id if calling_rule_id.isdigit() else 0
            endpoint.find_me = True if form_result.get('find_me')=="true" else False
            endpoint.auto_provision = True if form_result.get('auto_provision')=="true" else False
            endpoint.device_type_id = form_result.get('device_type_id') if form_result.get('device_type_id') else 0
            endpoint.include_xml_directory = True if form_result.get('include_xml_directory')=="true" else False
            endpoint.mac = form_result.get('mac', None)

            db.add(endpoint)
            db.flush()
            db.commit()

            route = PbxRoute()
            route.context = session['context']
            route.domain = session['context']
            route.name = form_result.get("extension")
            route.continue_route = True
            route.voicemail_enable = True
            route.voicemail_ext = form_result.get("extension")
            route.pbx_route_type_id = 1
            route.pbx_to_id = endpoint.id

            db.add(route)
            db.flush()
            db.commit()

            condition = PbxCondition()
            condition.context = session['context']
            condition.domain = session['context']
            condition.field = u'destination_number'
            condition.expression = u'^('+form_result.get("extension")+')$'
            condition.pbx_route_id = route.id

            db.add(condition)
            db.flush()
            db.commit()

            action = PbxAction()
            action.pbx_condition_id = condition.id
            action.context = session['context']
            action.domain = session['context']
            action.precedence = 1
            action.application = u'set'
            action.data = u'hangup_after_bridge=true'

            db.add(action)
            db.flush()
            db.commit()

            action = PbxAction()
            action.pbx_condition_id = condition.id
            action.context = session['context']
            action.domain = session['context']
            action.precedence = 1
            action.application = u'set'
            action.data = u'continue_on_fail=true'

            db.add(action)
            db.flush()
            db.commit()

            action = PbxAction()
            action.pbx_condition_id = condition.id
            action.context = session['context']
            action.domain = session['context']
            action.precedence = 2
            action.application = u'set'
            action.data = u'call_timeout='+form_result.get('call_timeout', 20)

            db.add(action)
            db.flush()
            db.commit()

            action = PbxAction()
            action.pbx_condition_id = condition.id
            action.context = session['context']
            action.domain = session['context']
            action.precedence = 3
            action.application = u'bridge'
            action.data = u'{force_transfer_context='+session['context']+'}sofia/'\
                     +str(get_profile())+'/'+form_result.get("extension")+'%'+session['context']

            db.add(action)
            db.flush()
            db.commit()

        except validators.Invalid, e:
            db.remove()
            return 'Validation Error: %s' % e

        return "Successfully added extension %s" % form_result.get('extension')

    @restrict("POST")
    @authorize(logged_in)
    def edit_extension(self, **kw):
        schema = ExtEditForm()
        try:
            form_result = schema.to_python(request.params)
            endpoint = PbxEndpoint.query.filter(PbxEndpoint.id==form_result.get('extension_id')).filter(PbxEndpoint.user_context==session['context']).first()
            endpoint.password = form_result.get('password')
            endpoint.outbound_caller_id_name = form_result.get('outbound_caller_id_name')
            endpoint.outbound_caller_id_number = form_result.get('outbound_caller_id_number')
            endpoint.internal_caller_id_name = form_result.get('internal_caller_id_name')
            endpoint.internal_caller_id_number = form_result.get('internal_caller_id_number')
            endpoint.vm_email = form_result.get('vm_email')
            endpoint.vm_password = form_result.get('vm_password')
            endpoint.vm_attach_email = True if form_result.get('vm_attach_email')=="true" else False
            endpoint.vm_notify_email = True if form_result.get('vm_notify_email')=="true" else False
            endpoint.vm_save = True if form_result.get('vm_save')=="true" else False
            endpoint.transfer_fallback_extension = form_result.get('transfer_fallback_extension')
            endpoint.follow_me_1 = form_result.get('follow_me_1')
            endpoint.follow_me_2 = form_result.get('follow_me_2')
            endpoint.follow_me_3 = form_result.get('follow_me_3')
            endpoint.follow_me_4 = form_result.get('follow_me_4')
            endpoint.call_timeout = form_result.get('call_timeout')
            time_dest = form_result.get('timeout_destination')
            endpoint.find_me = True if form_result.get('find_me')=="true" else False
            endpoint.timeout_destination = time_dest if time_dest.isdigit() else None
            endpoint.record_inbound_calls = form_result.get('record_inbound_calls', False)
            endpoint.record_outbound_calls = form_result.get('record_outbound_calls', False)
            endpoint.auto_provision = True if form_result.get('auto_provision')=="true" else False
            endpoint.device_type_id = form_result.get('device_type_id') if form_result.get('device_type_id') else 0
            endpoint.include_xml_directory = True if form_result.get('include_xml_directory')=="true" else False
            endpoint.mac = form_result.get('mac', None)
            endpoint.calling_rule_id = 0 if form_result.get('calling_rule_id', None) is not None else int(form_result.get('calling_rule_id', None))

            db.add(endpoint)
            db.flush()
            db.commit()

            route = PbxRoute.query.filter(PbxRoute.pbx_route_type_id==1).\
            filter(PbxRoute.name==endpoint.auth_id).filter(PbxRoute.context==session['context']).first()

            delete_conditions(route.id)

            condition = PbxCondition()
            condition.context = session['context']
            condition.domain = session['context']
            condition.field = u'destination_number'
            condition.expression = u'^('+endpoint.auth_id+')$'
            condition.pbx_route_id = route.id

            db.add(condition)
            db.flush()
            db.commit()

            action = PbxAction()
            action.pbx_condition_id = condition.id
            action.context = session['context']
            action.domain = session['context']
            action.precedence = 1
            action.application = u'set'
            action.data = u'hangup_after_bridge=true'

            db.add(action)
            db.flush()
            db.commit()

            action = PbxAction()
            action.pbx_condition_id = condition.id
            action.context = session['context']
            action.domain = session['context']
            action.precedence = 1
            action.application = u'set'
            action.data = u'continue_on_fail=true'

            db.add(action)
            db.flush()
            db.commit();

            action = PbxAction()
            action.pbx_condition_id = condition.id
            action.context = session['context']
            action.domain = session['context']
            action.precedence = 2
            action.application = u'set'
            action.data = u'call_timeout='+form_result.get('call_timeout', 20)

            db.add(action)
            db.flush()
            db.commit()

            action = PbxAction()
            action.pbx_condition_id = condition.id
            action.context = session['context']
            action.domain = session['context']
            action.precedence = 3
            action.application = u'bridge'
            action.data = u'{force_transfer_context='+session['context']+'}sofia/'+str(get_profile())+'/'+endpoint.auth_id+'%'+session['context']

            db.add(action)
            db.flush()
            db.commit()
            db.remove()

            db.remove()
            return "Successfully edited extension %s." % endpoint.auth_id

        except validators.Invalid, e:
            return 'Validation Error: %s' % e



    @authorize(logged_in)
    def update_ext_grid(self, **kw):

        try:

            w = loads(urllib.unquote_plus(request.params.get("data")))

            e = None

            for i in w['modified']:
                if i['name'].isdigit():
                    id = i['name']
                    u = User.query.filter(User.id==int(id)).filter_by(customer_id=session['customer_id']).first()
                    e = PbxEndpoint.query.filter(PbxEndpoint.auth_id==i['extension']).filter_by(user_context=session['context']).first()
                    e.user_id = u.id
                else:
                    e = PbxEndpoint.query.filter(PbxEndpoint.auth_id==i['extension']).filter_by(user_context=session['context']).first()

                e.password = i['password']

                db.commit(); db.flush()
                db.remove()

        except Exception, e:
            return "Error: %s" % e

        return "Successfully updated extension."

    @restrict("GET")
    @authorize(logged_in)
    def del_ext(self, **kw):

        try:
            delete_extension_by_ext(request.params['extension'])
        except:
            return "Error deleting extension."

        return  "Successfully deleted extension."

    @authorize(logged_in)
    @jsonify
    def vextensions(self):
        items=[]

        try:

            for extension in PbxVirtualExtension.query.filter_by(context=session['context']).all():
                items.append({'id': extension.id, 'extension': extension.extension, 'did': extension.did,
                              'timeout': extension.timeout, 'pbx_route_id': extension.pbx_route_id})

            db.remove()
            return {'identifier': 'id', 'label': 'extension', 'items': items}

        except KeyError, e:
            db.remove()
            return {'identifier': 'id', 'label': 'extension', 'items': [], 'is_error': True, 'message': 'KeyError: ' + str(e)}

        except Exception, e:
            db.remove()
            return {'identifier': 'id', 'label': 'extension', 'items': [], 'is_error': True, 'message': 'Exception: ' + str(e)}

    @authorize(logged_in)
    def vextension_add(self, **kw):
        schema = VirtualExtensionForm()
        try:
            form_result = schema.to_python(request.params)
            virtual_extension = PbxVirtualExtension()
            virtual_extension.extension = form_result.get('vextension_number')
            virtual_extension.did = form_result.get('vextension_did')
            virtual_extension.context = session['context']
            virtual_extension.timeout = form_result.get('timeout')
            virtual_extension.pbx_route_id = form_result.get('no_answer_destination')

            db.add(virtual_extension)
            db.flush()
            db.commit()

            route = PbxRoute()
            route.context = session['context']
            route.domain = session['context']
            route.name = form_result.get('vextension_number')
            route.continue_route = True
            route.voicemail_enable = True
            route.voicemail_ext = form_result.get('vextension_number')
            route.pbx_route_type_id = 2
            route.pbx_to_id = virtual_extension.id

            db.add(route)
            db.flush()
            db.commit()

        except validators.Invalid, error:
            return 'Validation Error: %s' % error

        db.remove()
        return "Successfully created virtual extension."

    @restrict("GET")
    @authorize(logged_in)
    def del_vext(self, **kw):

        try:
            delete_virtual_extension(request.params['extension'])
        except:
            return "Error deleting virtual extension."

        return  "Successfully deleted virtual extension."

    @authorize(logged_in)
    def update_vext_grid(self, **kw):

        try:
            w = loads(urllib.unquote_plus(request.params.get("data")))

            for i in w['modified']:
                if not len(i['did']) == 10 or not str(i['did']).strip().isdigit():
                    return "A virtual extension needs to be exactly 10 digits."
                virtual_extension = PbxVirtualExtension.query.filter_by(id=i['id']).filter_by(context=session['context']).first()
                virtual_extension.did = i['did']
                virtual_extension.timeout = i['timeout']
                virtual_extension.pbx_route_id = i['pbx_route_id']
                db.flush()
                db.commit()

        except DataInputError, error:
            db.remove()
            return 'Error: %s' % error

        return "Successfully updated virtual extension."

    @authorize(logged_in)
    @jsonify
    def vmboxes(self):
        items=[]
        try:
            for virtual_mailbox in PbxVirtualMailbox.query.filter_by(context=session['context']).all():
                items.append({'id': virtual_mailbox.id, 'extension': virtual_mailbox.extension, 'vm_password': virtual_mailbox.vm_password})
            db.remove()

            return {'identifier': 'id', 'label': 'extension', 'items': items}

        except Exception, e:
            return {'identifier': 'id', 'label': 'extension', 'items': [], 'is_error': True, 'message': 'Exception: ' + str(e)}

    @authorize(logged_in)
    @jsonify
    def calling_rules(self):
        items=[]

        try:
            for rule in PbxCallingRule.query.all():
                items.append({'id': rule.id, 'name': rule.name})

            db.remove()

            return {'identifier': 'id', 'label': 'name', 'items': items}

        except Exception, e:
            return {'identifier': 'id', 'label': 'name', 'items': [], 'is_error': True, 'message': 'Exception: ' + str(e)}


    @authorize(logged_in)
    @jsonify
    def vmbox_by_id(self, id, **kw):
        items=[]
        try:
            extension = PbxVirtualMailbox.query.filter_by(context=session['context']).filter_by(id=id).first()
            items.append({'id': extension.id, 'extension': extension.extension, 'vm_password': extension.vm_password,
                          'skip_greeting': extension.skip_greeting, 'audio_file': extension.audio_file,
                          'vm_email': extension.vm_email, 'vm_attach_email': extension.vm_attach_email,
                          'vm_notify_email': extension.vm_notify_email, 'vm_save': extension.vm_save})
            db.remove()

            return {'identifier': 'id', 'label': 'extension', 'items': items}

        except Exception, e:
            return {'identifier': 'id', 'label': 'extension', 'items': [], 'is_error': True, 'message': 'Exception: ' + str(e)}


    @authorize(logged_in)
    def vmbox_edit(self, **kw):
        schema = VirtualMailboxEditForm()
        try:
            form_result = schema.to_python(request.params)

            virtual_mailbox = PbxVirtualMailbox.query.filter_by(id=form_result.get('vmbox_id'))\
                        .filter_by(context=session['context']).first()
            virtual_mailbox.vm_password = form_result.get('vm_password')
            virtual_mailbox.context = session['context']
            virtual_mailbox.skip_greeting =  True if form_result.get('skip_greeting')=="true" else False
            virtual_mailbox.audio_file = form_result.get('audio_file', None)
            virtual_mailbox.vm_email = form_result.get('vm_email', None)
            virtual_mailbox.vm_password = form_result.get('vm_password', u'9999')
            virtual_mailbox.vm_attach_email = True if form_result.get('vm_attach_email')=="true" else False
            virtual_mailbox.vm_notify_email = True if form_result.get('vm_notify_email')=="true" else False
            virtual_mailbox.vm_save = True if form_result.get('vm_save')=="true" else False

            PbxRoute.query.filter_by(pbx_route_type_id=3).filter_by(pbx_to_id=virtual_mailbox.id).delete()
            db.flush()
            db.commit()

            route = PbxRoute()
            route.context = session['context']
            route.domain = session['context']
            route.name = virtual_mailbox.extension
            route.continue_route = True
            route.voicemail_enable = True
            route.voicemail_ext = virtual_mailbox.extension
            route.pbx_route_type_id = 3
            route.pbx_to_id = virtual_mailbox.id

            db.add(r)
            db.flush()
            db.commit()

        except validators.Invalid, error:
            return 'Validation Error: %s' % error

        db.remove()
        return "Successfully added virtual voicemail box."

    @authorize(logged_in)
    def vmbox_add(self, **kw):
        schema = VirtualMailboxForm()
        try:
            form_result = schema.to_python(request.params)
            virtual_mailbox = PbxVirtualMailbox()
            virtual_mailbox.extension = form_result.get('vmbox_number')
            virtual_mailbox.vm_password = form_result.get('vm_password')
            virtual_mailbox.context = session['context']
            virtual_mailbox.skip_greeting =  True if form_result.get('skip_greeting')=="true" else False
            virtual_mailbox.audio_file = form_result.get('audio_file', None)
            virtual_mailbox.vm_email = form_result.get('vm_email', None)
            virtual_mailbox.vm_password = form_result.get('vm_password', u'9999')
            virtual_mailbox.vm_attach_email = True if form_result.get('vm_attach_email')=="true" else False
            virtual_mailbox.vm_notify_email = True if form_result.get('vm_notify_email')=="true" else False
            virtual_mailbox.vm_save = True if form_result.get('vm_save')=="true" else False

            db.add(virtual_mailbox)
            db.flush()
            db.commit()

            route = PbxRoute()
            route.context = session['context']
            route.domain = session['context']
            route.name = form_result.get('vmbox_number')
            route.continue_route = True
            route.voicemail_enable = True
            route.voicemail_ext = form_result.get('vmbox_number')
            route.pbx_route_type_id = 3
            route.pbx_to_id = virtual_mailbox.id

            db.add(route)
            db.flush()
            db.commit()

        except validators.Invalid, error:
            return 'Validation Error: %s' % error

            db.remove()
            return "Successfully added virtual voicemail box."

    @authorize(logged_in)
    def update_vmbox_grid(self, **kw):

        try:
            w = loads(urllib.unquote_plus(request.params.get("data")))

            for i in w['modified']:
                if not str(i['extension']).strip().isdigit() or not str(i['pin']).strip().isdigit():
                    return "A virtual mailbox and pin needs to be exactly 3 or 4 numbers."
                virtual_mailbox = PbxVirtualMailbox.query.filter_by(id=i['id']).filter_by(context=session['context']).first()
                virtual_mailbox.vm_password = i['vm_password'].strip()
                db.flush()
                db.commit()
                db.remove()

        except DataInputError, error:
            db.remove()
            return 'Error: %s' % error

        return "Successfully updated virtual mailbox."

    @restrict("GET")
    @authorize(logged_in)
    def del_vmbox(self, **kw):

        try:
            delete_virtual_mailbox(request.params['extension'])
        except:
            return "Error deleting virtual mailbox."

        return  "Successfully deleted virtual mailbox."

    @authorize(logged_in)
    @jsonify
    def groups(self):
        items=[]

        try:
            for group in PbxGroup.query.filter_by(context=session['context']).all():
                members = []
                for extension in PbxGroupMember.query.filter_by(pbx_group_id=group.id).all():
                    members.append(extension.extension)
                items.append({'id': group.id, 'name': group.name, 'ring_strategy': group.ring_strategy,
                              'no_answer_destination': group.no_answer_destination, 'members': ",".join(members),
                              'timeout': group.timeout})

            db.remove()

            return {'identifier': 'id', 'label': 'name', 'items': items}

        except Exception, e:
            return {'identifier': 'id', 'label': 'name', 'items': [], 'is_error': True, 'message': str(e)}

    @authorize(logged_in)
    @jsonify
    def group_by_id(self, id, **kw):
        items=[]
        members=[]
        try:
            group = PbxGroup.query.filter_by(context=session['context']).filter_by(id=id).first()
            for extension in PbxGroupMember.query.filter_by(pbx_group_id=group.id).all():
                members.append(extension.extension)
            items.append({'id': group.id, 'name': group.name, 'ring_strategy': group.ring_strategy,
                          'no_answer_destination': group.no_answer_destination, 'members': ",".join(members),
                          'timeout': group.timeout})
            db.remove()

            return {'identifier': 'id', 'label': 'name', 'items': items}

        except Exception, e:
            return {'identifier': 'id', 'label': 'name', 'items': [], 'is_error': True, 'message': str(e)}

    @authorize(logged_in)
    def group_add(self, **kw):
        schema = GroupForm()
        try:
            form_result = schema.to_python(request.params)

            if len(form_result.get('group_extensions').split(","))==1:
                return "Error: You need to have at least two extensions to make a group."

            group = PbxGroup()
            group.name = form_result.get('group_name')
            group.context = session['context']
            group.ring_strategy = form_result.get('group_ring_strategy', 'sim')
            group.no_answer_destination = form_result.get('no_answer_destination', None)
            group.timeout = form_result.get('timeout', 13)

            db.add(group)
            db.flush()

            if not form_result.get('group_extensions').split(","):
                if not form_result.get('group_extensions').isdigit():
                    return "You need to have at least one extension to make a group."
                else:
                    db.add(PbxGroupMember(group.id, form_result.get('group_extensions')))
                    db.flush()
            else:
                for ext in form_result.get('group_extensions').split(","):
                    if not ext.isdigit():
                        continue
                    db.add(PbxGroupMember(group.id, ext))
                    db.flush()

            route = PbxRoute()
            route.context = session['context']
            route.domain = session['context']
            route.name = form_result.get('group_name')
            route.continue_route = True
            route.voicemail_enable = True
            route.voicemail_ext = form_result.get('group_name')
            route.pbx_route_type_id = 4
            route.pbx_to_id = group.id

            db.add(route)
            db.flush()
            db.commit()
            db.remove()

            return "Successfully added group "+str(form_result.get('group_name'))+"."

        except validators.Invalid, error:
            db.remove()
            return 'Validation Error: %s' % error

    @authorize(logged_in)
    def group_edit(self, **kw):
        schema = GroupEditForm()
        try:
            form_result = schema.to_python(request.params)

            if len(form_result.get('group_extensions').split(","))==1:
                return "Error: You need to have at least two extensions to make a group."

            db.delete(PbxGroup.query.filter_by(id=form_result.get('group_id')).first())

            for member in PbxGroupMember.query.filter_by(pbx_group_id=form_result.get('group_id')).all():
                db.delete(member)

            db.delete(PbxRoute.query.filter_by(pbx_route_type_id=4).filter_by(pbx_to_id=form_result.get('group_id')).first())
            db.flush()
            db.commit()

            group = PbxGroup()
            group.name = form_result.get('group_name')
            group.context = session['context']
            group.ring_strategy = form_result.get('group_ring_strategy', 'sim')
            group.no_answer_destination = form_result.get('no_answer_destination', None)
            group.timeout = form_result.get('timeout', 13)

            db.add(group)
            db.flush()
            db.commit()

            if not form_result.get('group_extensions').split(","):
                if not form_result.get('group_extensions').isdigit():
                    return "You need to have at least one extension to make a group."
                else:
                    db.add(PbxGroupMember(group.id, form_result.get('group_extensions')))
                    db.commit()
                    db.flush()
            else:
                for ext in form_result.get('group_extensions').split(","):
                    if not ext.isdigit():
                        continue
                    db.add(PbxGroupMember(group.id, ext))
                    db.commit()
                    db.flush()

            route = PbxRoute()
            route.context = session['context']
            route.domain = session['context']
            route.name = form_result.get('group_name')
            route.continue_route = True
            route.voicemail_enable = True
            route.voicemail_ext = form_result.get('group_name')
            route.pbx_route_type_id = 4
            route.pbx_to_id = group.id

            db.add(route)
            db.flush()
            db.commit()
            db.remove()

        except validators.Invalid, error:
            db.remove()
            return 'Validation Error: %s' % error

        return "Successfully added group "+str(form_result.get('group_name'))+"."

    @authorize(logged_in)
    def update_group_grid(self, **kw):

        w = loads(urllib.unquote_plus(request.params.get("data")))

        try:
            for i in w['modified']:
                group = PbxGroup.query.filter_by(id=i['id']).first()
                group.no_answer_destination = i['no_answer_destination']
                group.ring_strategy = i['ring_strategy']
                db.flush()
                db.commit()

                PbxGroupMember.query.filter(PbxGroupMember.pbx_group_id==i['id']).delete()

                for group_member in i['members'].split(","):
                    if not group_member.strip().isdigit():
                        continue
                    db.add(PbxGroupMember(i['id'], group_member.strip()))
                    db.commit()
                    db.flush()
        except:
            db.remove()
            return "Error updating group."

        return "Successfully updated group."

    @restrict("GET")
    @authorize(logged_in)
    def del_group(self, **kw):

        try:
            delete_group(request.params['name'])
        except:
            return "Error"

        return  "Successfully deleted group."

    @authorize(logged_in)
    @jsonify
    def dids(self):
        items=[]

        try:
            for did in PbxDid.query.filter_by(context=session['context']).all():
                route = db.query(PbxRoute.id, PbxRouteType.name, PbxRoute.name)\
                            .join(PbxRouteType).filter(PbxRoute.context==session['context'])\
                            .filter(PbxRoute.id==did.pbx_route_id).first()
                if route:
                    items.append({'id': did.id, 'did': did.did, 'route_name': route[1]+': '+route[2], 'pbx_route_id': route.id})
                else:
                    items.append({'id': did.id, 'did': did.did, 'route_name': "Broken Route!", 'pbx_route_id': 0})

            lbid = get_route_labels_ids()
            db.remove()

            return {'identifier': 'id', 'label': 'name', 'items': items,'did_labels': lbid[0], 'did_ids': lbid[1]}

        except Exception, e:
            return {'identifier': 'id', 'label': 'name', 'items': [], 'did_labels': None, 'did_ids': None, 'is_error': True, 'message': str(e)}

    @authorize(logged_in)
    def update_did_grid(self, **kw):

        w = loads(urllib.unquote_plus(request.params.get("data")))

        try:
            for i in w['modified']:
                did = PbxDid.query.filter_by(id=i['id']).filter_by(context=session['context']).first()
                did.pbx_route_id = i['route_name']
                db.flush()
                db.commit()
                db.commit()
        except:
            db.remove()
            return "Error updating DID."

        return "Successfully updated DID."

    @authorize(logged_in)
    @jsonify
    def faxes(self):
        files = []
        dir = fs_vm_dir+session['context']+"/faxes"

        try:
            for i in os.listdir(dir):
                if not i.endswith(".png"):
                    continue
                path = dir+"/"+i
                uuid = i.split("_")[0].strip()
                name = i.split("_")[1].strip().split(".")[0]

                if name.find("-") == -1:
                    page_num = "Single Page"
                else:
                    page_num = name.split("-")[1].split(".")[0].strip()
                    name = name.split("-")[0].strip()
                    page_num = int(page_num)+1

                tpath = "/vm/" +session['context']+"/faxes/"+i
                received = str(modification_date(path)).strip("\"")
                fsize = str(os.path.getsize(path))
                cdr = PbxCdr.query.filter(PbxCdr.uuid==uuid).first()
                if cdr:
                    caller = cdr.caller_id_number[len(cdr.caller_id_number)-10:]
                else:
                    caller = "Unknown"
                files.append({'uuid': uuid, 'name': name, 'caller_id': caller, 'path': tpath, 'received': received, 'size': fsize, 'page_num': page_num})
        except:
            os.makedirs(dir)

        db.remove()
        return {'identifier': 'path', 'label': 'name', 'items': files}

    @authorize(logged_in)
    def fax_add(self, **kw):
        schema = FaxForm()
        try:
            form_result = schema.to_python(request.params)
            fax = PbxFax()
            fax.extension = form_result.get('fax_name')
            fax.context = session['context']

            db.add(fax)
            db.flush()
            db.commit()

            router = PbxRoute()
            router.context = session['context']
            router.domain = session['context']
            router.name = form_result.get('fax_name')
            router.continue_route = False
            router.voicemail_enable = False
            router.voicemail_ext = form_result.get('fax_name')
            router.pbx_route_type_id = 12
            router.pbx_to_id = fax.id

            db.add(router)
            db.flush()
            db.commit()

        except validators.Invalid, e:
            db.remove()
            return 'Validation Error: Please correct form inputs and resubmit: %s' %e

    @authorize(logged_in)
    @jsonify
    def fax_ext(self):
        items=[]

        try:
            for ext in PbxFax.query.filter_by(context=session['context']).all():
                items.append({'id': ext.id, 'extension': ext.extension})

            db.remove()

            return {'identifier': 'id', 'label': 'extension', 'items': items}

        except Exception, e:
            return {'identifier': 'id', 'label': 'extension', 'items': [], 'is_error': True, 'messages': str(e)}

    @authorize(logged_in)
    def fax_send(self, **kw):
        form = cgi.FieldStorage()

        user = User.query.filter_by(session_id=session.id).first()
        if not user:
            return

        ep = db.execute("SELECT pbx_dids.did FROM pbx_dids "
                        "INNER JOIN pbx_routes on pbx_dids.pbx_route_id = pbx_routes.id "
                        "WHERE pbx_routes.pbx_route_type_id=12").fetchone()

        if ep:
            if len(ep[0])==10:
                origination_caller_id_number = ep[0]
            else:
                origination_caller_id_number = ep[1]
        else:
            origination_caller_id_number = "0000000000"

        myfile = request.params['uploadedfiles[]']

        fname = myfile.filename.lstrip(os.sep)
        ext = fname.split(".")[len(fname.split("."))-1]
        if not ext:
            return  "Error no file type found."
        fname = re.sub('[^A-Za-z0-9]+', '', fname)
        fname = fname+"."+ext

        try:
            dir = "/tmp/"
            permanent_file = open(os.path.join(dir,fname), 'w')
            shutil.copyfileobj(myfile.file, permanent_file)
            myfile.file.close()
            permanent_file.close()
        except:
            return "Error uploading file. The administrator has been contacted."

        converted = fname.split(".")[0]+".tiff"
        call("convert -density 204x98 -units PixelsPerInch -resize 1728x1186\! -monochrome -compress Fax /tmp/"+fname+" /tmp/"+converted, shell=True)
        os.remove("/tmp/"+fname)

        con = ESLconnection(ESL_HOST, ESL_PORT, ESL_PASS)
        if con.connected:
            con.bgapi("originate", "{fax_ident='FreePyBX Web Fax',fax_header="+str(origination_caller_id_number)+",fax_enable_t38=true,origination_caller_id_number="+str(origination_caller_id_number)+"}sofia/gateway/voipinnovations/"+str(request.params["fax_recipient"])+" &txfax(/tmp/"+str(converted)+")")

    @restrict("GET")
    @authorize(logged_in)
    def del_fax(self, **kw):
        """For security, we check the input, then put them into their own context"""

        file_name = request.params['name'].split("/")[len(request.params['name'].split("/"))-1]

        try:
            dir = fs_vm_dir+session['context']+"/faxes/"+file_name
            os.remove(dir)
        except:
            return "Error deleting fax."
        return "Deleted fax."

    @authorize(logged_in)
    def del_fax_ext(self, **kw):

        try:
            delete_fax_ext(request.params['name'])
        except:
            return "Error deleting fax extension."

        return  "Successfully deleted fax extension."

    @authorize(logged_in)
    @jsonify
    def tod_routes(self):
        items=[]

        try:
            for tod in PbxTODRoute.query.filter_by(context=session['context']).all():
                route_match = db.query(PbxRoute.id, PbxRouteType.name, PbxRoute.name)\
                .join(PbxRouteType).filter(PbxRoute.context==session['context']).filter(PbxRoute.id==tod.match_route_id).first()
                route_nomatch = db.query(PbxRoute.id, PbxRouteType.name, PbxRoute.name)\
                .join(PbxRouteType).filter(PbxRoute.context==session['context']).filter(PbxRoute.id==tod.nomatch_route_id).first()

                items.append({'id': tod.id, 'name': tod.name, 'day_start': tod.day_start, 'day_end': tod.day_end, 'time_start': tod.time_start[1:len(tod.time_start)-3], 'time_end': tod.time_end[1:len(tod.time_end)-3],
                              'match_route_id': tod.match_route_id, 'nomatch_route_id': tod.nomatch_route_id, 'match_name': route_match[1]+': '+route_match[2],
                              'match_id': route_match[0], 'nomatch_name': route_nomatch[1]+': '+route_nomatch[2], 'nomatch_id': route_nomatch[0]})
            db.remove()
            return {'identifier': 'id', 'label': 'extension', 'items': items}
        except Exception, e:
            return {'identifier': 'id', 'label': 'extension', 'items': [], 'is_error': True, 'messages': str(e)}

    @authorize(logged_in)
    def tod_route_add(self, **kw):
        schema = TODForm()
        try:
            form_result = schema.to_python(request.params)
            time_of_day_route = PbxTODRoute()
            time_of_day_route.domain = session['context']
            time_of_day_route.context = session['context']
            time_of_day_route.name = form_result.get('name')
            time_of_day_route.day_start = form_result.get('day_start')
            time_of_day_route.day_end = form_result.get('day_end')
            time_of_day_route.time_start = form_result.get('time_start')
            time_of_day_route.time_end = form_result.get('time_end')
            time_of_day_route.match_route_id = form_result.get('match_route_id')
            time_of_day_route.nomatch_route_id = form_result.get('nomatch_route_id')

            db.add(time_of_day_route)
            db.flush()
            db.commit()

            route = PbxRoute()
            route.context = session['context']
            route.domain = session['context']
            route.name = form_result.get('name')
            route.continue_route = True
            route.voicemail_enable = True
            route.voicemail_ext = form_result.get('name')
            route.pbx_route_type_id = 6
            route.pbx_to_id = time_of_day_route.id

            db.add(route)
            db.flush()
            db.commit()

        except validators.Invalid, error:
            return 'Error: %s' % error

        db.remove()
        return "Successfully added time of day route."

    @authorize(logged_in)
    @jsonify
    def tod_by_id(self, id, **kw):
        items=[]
        try:
            time_of_day_route = PbxTODRoute.query.filter_by(id=id).filter_by(context=session['context']).first()
            items.append({'id': time_of_day_route.id, 'name': time_of_day_route.name, 'day_start': time_of_day_route.day_start,
                          'day_end': time_of_day_route.day_end, 'time_start': time_of_day_route.time_start, 'time_end': time_of_day_route.time_end,
                          'match_route_id': time_of_day_route.match_route_id, 'nomatch_route_id': time_of_day_route.nomatch_route_id})

            return {'identifier': 'id', 'label': 'name', 'items': items}

        except Exception, e:
            return {'identifier': 'id', 'label': 'extension', 'items': [], 'is_error': True, 'messages': str(e)}

    @authorize(logged_in)
    def edit_tod(self, **kw):
        try:
            tod = PbxTODRoute.query.filter_by(context=session['context'])\
                .filter(PbxTODRoute.id==request.params.get('tod_id')).first()

            if not tod:
                return "Error: No route found with that id."

            tod.name = request.params.get('name')
            tod.store_id = request.params.get('store_id')
            tod.day_start = request.params.get('day_start')
            tod.day_end = request.params.get('day_end')
            tod.time_start = request.params.get('time_start')
            tod.time_end = request.params.get('time_end')
            tod.active = True if request.params.get('active')=="true" else False
            tod.match_route_id = request.params.get('match_route_id')
            tod.nomatch_route_id = request.params.get('nomatch_route_id')

            db.commit(); db.flush()
            db.remove()

        except validators.Invalid, error:
            db.remove()
            return 'Error: %s' % error

        return "Successfully updated time of day route."

    @restrict("GET")
    @authorize(logged_in)
    def del_tod(self, **kw):
        try:
            t = PbxTODRoute.query.filter(PbxTODRoute.id==request.params['id']).first()
            delete_tod(t.name)
        except:
            return "Error deleting Time of Day Route"

        return  "Successfully deleted Time of Day Route."

    @authorize(logged_in)
    @jsonify
    def recordings(self):
        files = []
        dir = fs_vm_dir+session['context']+"/recordings/"
        try:
            for i in os.listdir(dir):
                files.append(generateFileObject(i, "",  dir))
        except:
            os.makedirs(dir)
            for i in os.listdir(dir):
                files.append(generateFileObject(i, "",  dir))

        return {'identifier': 'name', 'label': 'name', 'items': files}

    @authorize(logged_in)
    @jsonify
    def audio_recordings(self):
        items = []
        dir = fs_vm_dir+session['context']+"/recordings/"
        try:
            for i in os.listdir(dir):
                fo = generateFileObject(i, "",  dir)
                items.append({'id': '1,'+fo["name"], 'name': 'Recording: '+fo["name"] , 'data': fo["path"], 'type': 1, 'real_id': ""})

            db.remove()
        except:
            pass

        return {'identifier': 'id', 'label': 'name', 'items': items}

    @restrict("POST")
    @authorize(logged_in)
    def delete_recording(self, **kw):

        ivr = PbxIVR.query.filter(PbxIVR.data==request.params['name']).filter(PbxIVR.context==session['context']).first()

        if t:
            return "Error: Recording "+request.params['name']+" is in use by IVR named "+ivr.name+"!"

        try:
            dir = fs_vm_dir+session['context']+"/recordings/"+request.params['name']
            os.remove(dir)
        except:
            db.remove()
            return "Error deleting recording."

        db.remove()
        return "Deleted recording."

    @authorize(logged_in)
    def upload_recording(self):

        myfile = request.params['uploadedfiles[]']

        if not myfile.filename.endswith(".wav"):
            return "Error uploading file. File must have .wav extension."

        try:
            dir = fs_vm_dir + "/"+session['context']+"/recordings/"
            permanent_file = open(os.path.join(dir,myfile.filename.lstrip(os.sep)), 'w')
            shutil.copyfileobj(myfile.file, permanent_file)
            myfile.file.close()
            permanent_file.close()
        except:
            return "Error uploading file. The administrator has been contacted."

        return "Successfully uploaded recording."

    @authorize(logged_in)
    def recording_name(self, **kw):
        files = []
        dir = fs_vm_dir+session['context']+"/recordings/"
        old_name = request.params['old_name']
        new_name = request.params['new_name']
        src = dir+old_name
        dst = dir+new_name

        if not new_name.endswith(".wav"):
            dst +=".wav"

        os.rename(src, dst)

        return "Successfully renamed recording"

    @authorize(logged_in)
    @jsonify
    def conferences(self):
        items=[]

        try:
            for conf in PbxConferenceBridge.query.filter_by(context=session['context']).all():
                items.append({'id': conf.id, 'extension': conf.extension, 'pin': conf.pin})

            db.remove()

            return {'identifier': 'id', 'label': 'extension', 'items': items}

        except Exception, e:
            return {'identifier': 'id', 'label': 'extension', 'items': [], 'is_error': True, 'messages': str(e)}


    @authorize(logged_in)
    def conf_add(self, **kw):
        schema = ConferenceForm()
        try:
            form_result = schema.to_python(request.params)
            conference_bridge = PbxConferenceBridge()
            conference_bridge.extension = form_result.get('extension')
            conference_bridge.pin = form_result.get('pin')
            conference_bridge.context = session['context']
            conference_bridge.domain = session['context']

            db.add(conference_bridge)
            db.flush()
            db.commit()

            route = PbxRoute()
            route.context = session['context']
            route.domain = session['context']
            route.name = form_result.get('extension')
            route.continue_route = False
            route.voicemail_enable = False
            route.voicemail_ext = form_result.get('extension')
            route.pbx_route_type_id = 7
            route.pbx_to_id = conference_bridge.id

            db.add(route)
            db.flush()
            db.commit()
            db.remove()

        except validators.Invalid, error:
            db.remove()
            return 'Validation Error: %s' % error

        return "Successfully added conference bridge."

    @restrict("GET")
    @authorize(logged_in)
    def del_conf(self, **kw):

        try:
            delete_conf(request.params['extension'])
        except:
            return "Error deleting conference bridge."

        return  "Successfully deleted conference bridge."

    @authorize(logged_in)
    @jsonify
    def cid_routes(self):
        items=[]
        try:
            for cid in PbxCallerIDRoute.query.filter_by(context=session['context']).all():
                route = db.query(PbxRoute.id, PbxRouteType.name, PbxRoute.name)\
                            .join(PbxRouteType).filter(PbxRoute.context==session['context']).filter(PbxRoute.id==cid.pbx_route_id).first()
                items.append({'id': cid.id, 'cid_number': cid.cid_number, 'pbx_route_id': cid.pbx_route_id, 'pbx_route_name': route[1]+': '+route[2]})

            db.remove()

            return {'identifier': 'id', 'label': 'cid_number', 'items': items}

        except Exception, e:
            return {'identifier': 'id', 'label': 'cid_number', 'items': [], 'is_error': True, 'messages': str(e)}

    @authorize(logged_in)
    def cid_add(self, **kw):
        schema = CIDForm()
        try:
            form_result = schema.to_python(request.params)
            cid = PbxCallerIDRoute()
            cid.cid_number = form_result.get('cid_number')
            cid.pbx_route_id = form_result.get('pbx_route_id')
            cid.context = session['context']
            cid.domain = session['context']

            db.add(cid)
            db.flush()
            db.commit()

        except validators.Invalid, error:
            db.remove()
            return 'Validation Error: %s' % error

        db.remove()
        return "Successfully added Caller ID Route."

    @restrict("GET")
    @authorize(logged_in)
    def del_cid(self, **kw):

        try:
            delete_cid(request.params['cid_number'])
        except:
            return "Error deleting CallerID Route."

        return  "Successfully deleted CallerID route."

    @authorize(logged_in)
    @jsonify
    def blacklisted(self):
        items=[]
        try:
            for cid in PbxBlacklistedNumber.query.filter_by(context=session['context']).all():
                items.append({'id': cid.id, 'cid_number': cid.cid_number})

            db.remove()

            return {'identifier': 'id', 'label': 'cid_number', 'items': items}

        except Exception, e:
            return {'identifier': 'id', 'label': 'cid_number', 'items': [], 'is_error': True, 'messages': str(e)}

    @authorize(logged_in)
    def blacklist_add(self, **kw):
        schema = PbxBlacklistedForm()
        try:
            form_result = schema.to_python(request.params)
            black_listed = PbxBlacklistedNumber()
            black_listed.cid_number = form_result.get('cid_number')
            black_listed.context = session['context']
            black_listed.domain = session['context']

            db.add(black_listed)
            db.flush()
            db.commit();

        except validators.Invalid, error:
            db.remove()
            return 'Validation Error: %s' % error

        db.remove()
        return "Successfully added to blacklist."

    @restrict("GET")
    @authorize(logged_in)
    def del_bl(self, **kw):

        try:
            del_blacklist(request.params['cid_number'])
        except:
            return "Error deleting blacklisted number."

        return  "Successfully deleted blacklisted number."

    @authorize(logged_in)
    @jsonify
    def tts(self):
        items=[]
        try:
            for test_to_speech in PbxTTS.query.filter_by(context=session['context']).all():
                items.append({'id': test_to_speech.id, 'name': test_to_speech.name, 'text': test_to_speech.text})

            db.remove()

            return {'identifier': 'id', 'label': 'name', 'items': items}

        except Exception, e:
            return {'identifier': 'id', 'label': 'name', 'items': [], 'is_error': True, 'messages': str(e)}

    @authorize(logged_in)
    def tts_add(self, **kw):
        schema = TTSForm()
        try:
            form_result = schema.to_python(request.params)
            test_to_speech = PbxTTS()
            test_to_speech.name = form_result.get('name')
            test_to_speech.text = form_result.get('tts_text')
            test_to_speech.context = session['context']
            test_to_speech.domain = session['context']
            test_to_speech.voice = u'Allison'

            db.add(test_to_speech)
            db.flush()
            db.commit()

        except validators.Invalid, error:
            db.remove()
            return 'Validation Error: %s' % error

        db.remove()
        return "Successfully added Text to Speech entry."

    @authorize(logged_in)
    def update_tts_grid(self, **kw):

        try:
            w = loads(urllib.unquote_plus(request.params.get("data")))

            for i in w['modified']:
                test_to_speech = PbxTTS.query.filter_by(id=i['id']).filter_by(context=session['context']).first()
                test_to_speech.name = i['name'].strip()
                test_to_speech.text = i['text'].strip()

                db.commit()
                db.flush()
                db.commit()

        except DataInputError, error:
            db.remove()
            return 'Error: %s' % error

        return "Successfully updated TTS entry."

    @restrict("GET")
    @authorize(logged_in)
    def del_tts(self, **kw):
        return  delete_tts(request.params['name'])

    @authorize(logged_in)
    @jsonify
    def ivr(self):
        items=[]
        try:
            for ivr in PbxIVR.query.filter_by(context=session['context']).all():
                items.append({'id': ivr.id, 'name': ivr.name})

            db.remove()

            return {'identifier': 'id', 'label': 'name', 'items': items}

        except Exception, e:
            return {'identifier': 'id', 'label': 'name', 'items': [], 'is_error': True, 'messages': str(e)}

    @authorize(logged_in)
    @jsonify
    def ivr_by_id(self, id, **kw):
        items=[]
        try:
            for ivr in PbxIVR.query.filter_by(context=session['context']).filter_by(id=id).all():
                options=[]
                for opt in PbxIVROption.query.filter_by(pbx_ivr_id=ivr.id).all():
                    options.append({'option': opt.option, 'pbx_route_id': opt.pbx_route_id})

                items.append({'id': ivr.id, 'name': ivr.name,'timeout': ivr.timeout, 'direct_dial': ivr.direct_dial, 'data': ivr.data,\
                              'audio_name': str(ivr.audio_type)+','+str(ivr.data), 'timeout_destination': ivr.timeout_destination, 'options': options})

            db.remove()

            return {'identifier': 'id', 'label': 'name', 'items': items}

        except Exception, e:
            return {'identifier': 'id', 'label': 'name', 'items': [], 'is_error': True, 'messages': str(e)}

    @authorize(logged_in)
    def ivr_add(self, **kw):
        schema = IVRForm()
        try:
            form_result = schema.to_python(request.params)
            ivr = PbxIVR()
            ivr.name = form_result.get('ivr_name')

            ivr.audio_type = form_result.get('audio_name').split(",")[0].strip()
            ivr.data = form_result.get('audio_name').split(",")[1].strip()
            ivr.domain = session['context']
            ivr.context = session['context']
            ivr.customer_id = session['customer_id']
            ivr.timeout = form_result.get('timeout')
            ivr.timeout_destination = form_result.get('timeout_destination')

            if request.params.has_key('direct_dial'):
                ivr.direct_dial = True
            else:
                ivr.direct_dial = False

            db.add(ivr)
            db.flush()
            db.commit()

            if len(form_result.get('option_1'))>0:
                ivr_option = PbxIVROption()
                ivr_option.option = 1
                ivr_option.pbx_ivr_id = ivr.id
                ivr_option.pbx_route_id = form_result.get('option_1')

                db.add(ivr_option)
                db.flush()
                db.commit()

            if len(form_result.get('option_2'))>0:
                ivr_option = PbxIVROption()
                ivr_option.option = 2
                ivr_option.pbx_ivr_id = ivr.id
                ivr_option.pbx_route_id = form_result.get('option_2')

                db.add(ivr_option)
                db.flush()
                db.commit()

            if len(form_result.get('option_3'))>0:
                ivr_option = PbxIVROption()
                ivr_option.option = 3
                ivr_option.pbx_ivr_id = ivr.id
                ivr_option.pbx_route_id = form_result.get('option_3')

                db.add(ivr_option)
                db.flush()
                db.commit()

            if len(form_result.get('option_4'))>0:
                ivr_option = PbxIVROption()
                ivr_option.option= 4
                ivr_option.pbx_ivr_id = ivr.id
                ivr_option.pbx_route_id = form_result.get('option_4')

                db.add(ivr_option)
                db.flush()
                db.commit()

            if len(form_result.get('option_5'))>0:
                ivr_option = PbxIVROption()
                ivr_option.option = 5
                ivr_option.pbx_ivr_id = ivr.id
                ivr_option.pbx_route_id = form_result.get('option_5')

                db.add(ivr_option)
                db.flush()
                db.commit()

            if len(form_result.get('option_6'))>0:
                ivr_option = PbxIVROption()
                ivr_option.option=6
                ivr_option.pbx_ivr_id = ivr.id
                ivr_option.pbx_route_id = form_result.get('option_6')

                db.add(ivr_option)
                db.flush()
                db.commit()

            if len(form_result.get('option_7'))>0:
                ivr_option = PbxIVROption()
                ivr_option.option=7
                ivr_option.pbx_ivr_id = ivr.id
                ivr_option.pbx_route_id = form_result.get('option_7')

                db.add(ivr_option)
                db.flush()
                db.commit()

            if len(form_result.get('option_8'))>0:
                ivr_option = PbxIVROption()
                ivr_option.option=8
                ivr_option.pbx_ivr_id = ivr.id
                ivr_option.pbx_route_id = form_result.get('option_8')

                db.add(ivr_option)
                db.flush()
                db.commit()

            if len(form_result.get('option_9'))>0:
                ivr_option = PbxIVROption()
                ivr_option.option=9
                ivr_option.pbx_ivr_id = ivr.id
                ivr_option.pbx_route_id = form_result.get('option_9')

                db.add(ivr_option)
                db.flush()
                db.commit()

            if len(form_result.get('option_0'))>0:
                ivr_option = PbxIVROption()
                ivr_option.option=0
                ivr_option.pbx_ivr_id = ivr.id
                ivr_option.pbx_route_id = form_result.get('option_0')

                db.add(ivr_option)
                db.flush()
                db.commit()

            route = PbxRoute()
            route.context = session['context']
            route.domain = session['context']
            route.name = form_result.get('ivr_name')
            route.continue_route = True
            route.voicemail_enable = True
            route.voicemail_ext = form_result.get('ivr_name')
            route.pbx_route_type_id = 5
            route.pbx_to_id = ivr.id

            db.add(route)
            db.flush()
            db.commit()
            db.remove()

            return "Successfully added IVR."

        except validators.Invalid, error:
            db.remove()
            return 'Validation Error: Please correct form inputs and resubmit.'


    @authorize(logged_in)
    def ivr_edit(self, **kw):
        schema = IVREditForm()
        try:
            form_result = schema.to_python(request.params)
            ivr = PbxIVR.query.filter_by(id=form_result.get('ivr_id')).filter_by(context=session['context']).first()

            ivr.name = form_result.get('ivr_name')
            ivr.audio_type = form_result.get('audio_name').split(",")[0].strip()
            ivr.data = form_result.get('audio_name').split(",")[1].strip()
            ivr.domain = session['context']
            ivr.context = session['context']
            ivr.timeout = form_result.get('timeout')
            ivr.timeout_destination=form_result.get('timeout_destination')

            if request.params.has_key('direct_dial'):
                ivr.direct_dial=True
            else:
                ivr.direct_dial=False

            db.flush()
            db.commit();

            PbxIVROption.query.filter_by(pbx_ivr_id=ivr.id).delete()
            db.flush()
            db.commit()

            if len(form_result.get('option_1'))>0:
                ivr_option = PbxIVROption()
                ivr_option.option = 1
                ivr_option.pbx_ivr_id = ivr.id
                ivr_option.pbx_route_id = form_result.get('option_1')

                db.add(ivr_option)
                db.flush()
                db.commit()

            if len(form_result.get('option_2'))>0:
                ivr_option = PbxIVROption()
                ivr_option.option = 2
                ivr_option.pbx_ivr_id = ivr.id
                ivr_option.pbx_route_id = form_result.get('option_2')

                db.add(ivr_option)
                db.flush()
                db.commit()

            if len(form_result.get('option_3'))>0:
                ivr_option = PbxIVROption()
                ivr_option.option = 3
                ivr_option.pbx_ivr_id = ivr.id
                ivr_option.pbx_route_id = form_result.get('option_3')

                db.add(ivr_option)
                db.flush()
                db.commit()

            if len(form_result.get('option_4'))>0:
                ivr_option = PbxIVROption()
                ivr_option.option= 4
                ivr_option.pbx_ivr_id = ivr.id
                ivr_option.pbx_route_id = form_result.get('option_4')

                db.add(ivr_option)
                db.flush()
                db.commit()

            if len(form_result.get('option_5'))>0:
                ivr_option = PbxIVROption()
                ivr_option.option = 5
                ivr_option.pbx_ivr_id = ivr.id
                ivr_option.pbx_route_id = form_result.get('option_5')

                db.add(ivr_option)
                db.flush()
                db.commit()

            if len(form_result.get('option_6'))>0:
                ivr_option = PbxIVROption()
                ivr_option.option=6
                ivr_option.pbx_ivr_id = ivr.id
                ivr_option.pbx_route_id = form_result.get('option_6')

                db.add(ivr_option)
                db.flush()
                db.commit()

            if len(form_result.get('option_7'))>0:
                ivr_option = PbxIVROption()
                ivr_option.option=7
                ivr_option.pbx_ivr_id = ivr.id
                ivr_option.pbx_route_id = form_result.get('option_7')

                db.add(ivr_option)
                db.flush()
                db.commit()

            if len(form_result.get('option_8'))>0:
                ivr_option = PbxIVROption()
                ivr_option.option=8
                ivr_option.pbx_ivr_id = ivr.id
                ivr_option.pbx_route_id = form_result.get('option_8')

                db.add(ivr_option)
                db.flush()
                db.commit()

            if len(form_result.get('option_9'))>0:
                ivr_option = PbxIVROption()
                ivr_option.option=9
                ivr_option.pbx_ivr_id = ivr.id
                ivr_option.pbx_route_id = form_result.get('option_9')

                db.add(ivr_option)
                db.flush()
                db.commit()

            if len(form_result.get('option_0'))>0:
                ivr_option = PbxIVROption()
                ivr_option.option=0
                ivr_option.pbx_ivr_id = ivr.id
                ivr_option.pbx_route_id = form_result.get('option_0')

                db.add(ivr_option)
                db.flush()
                db.commit()

            route = PbxRoute.query.filter_by(pbx_route_type_id=5, context=session['context'], pbx_to_id=ivr.id).first()
            route.name = form_result.get('ivr_name')
            route.voicemail_ext = form_result.get('ivr_name')
            db.flush()
            db.commit()

        except validators.Invalid, error:
            db.remove()
            return 'Validation Error: Please correct form inputs and resubmit.'

        db.remove()
        return "Successfully edited IVR."

    @authorize(logged_in)
    def update_ivr_grid(self, **kw):

        w = loads(urllib.unquote_plus(request.params.get("data")))

        try:
            for i in w['modified']:
                ivr = PbxIVR.query.filter_by(context=session['context']).filter(PbxIVR.id==int(i['id'])).first()
                ivr.name = i['name']

                route = PbxRoute.query.filter_by(context=session['context']).\
                filter(PbxRoute.pbx_route_type_id==5).filter(PbxRoute.pbx_to_id==int(i['id'])).first()
                route.name = i['name']

                db.flush()
                db.commit()
                db.remove()

                return "Successfully updated IVR."

        except Exception, e:
            return 'Error: %e' %e

    @restrict("GET")
    @authorize(logged_in)
    def del_ivr(self, **kw):
        return  delete_ivr(request.params['name'])

    @authorize(logged_in)
    @jsonify
    def ivr_audio(self):
        items = []
        dir = fs_vm_dir+session['context']+"/recordings/"

        try:
            for i in os.listdir(dir):
                fo = generateFileObject(i, "",  dir)
                items.append({'id': '1,'+fo["name"], 'name': 'Recording: '+fo["name"] , 'data': fo["path"], 'type': 1, 'real_id': ""})
        except:
            os.makedirs(dir)

        try:
            for test_to_speech in PbxTTS.query.filter_by(context=session['context']).all():
                items.append({'id': '2,'+str(test_to_speech.id), 'name': 'TTS: '+ test_to_speech.name, 'data': test_to_speech.text, 'type': 2, 'real_id': test_to_speech.id})

            return {'identifier': 'id', 'label': 'name', 'items': items}

        except Exceptoin, e:
            return {'identifier': 'id', 'label': 'name', 'items': [], 'is_error': True, 'messages': str(e)}

    @authorize(logged_in)
    @jsonify
    def voicemail_from_file_system(self):
        files = []

        dir = fs_vm_dir+session['context']+"/"+session['ext']

        try:
            for i in os.listdir(dir):
                if i.startswith("greeting_"):
                    continue
                id = i.split("_")[1].split(".")[0].strip()
                row = PbxCdr.query.filter(PbxCdr.uuid==id).first()
                path = dir+"/"+i
                tpath = "/vm/"+session['context']+"/"+session['ext']+"/"+i
                received = str(modification_date(path)).strip("\"")
                fsize = str(os.path.getsize(path))
                caller = row.caller_id_number[len(row.caller_id_number)-10:]
                files.append({'name': caller, 'path': tpath, 'received': received, 'size': fsize})

            return {'identifier': 'path', 'label': 'name', 'items': files}
        except:
            os.makedirs(dir)
            return {'identifier': 'path', 'label': 'name', 'items': []}

    @authorize(logged_in)
    @jsonify
    def voicemail(self):
        items=[]
        path = []
        i = 4
        try:
            if session['group_id'] > 1:
                voice_mails = VoiceMail.query.filter_by(domain=session['context']).filter(VoiceMail.username==session['ext']).all()
            else:
                voice_mails = VoiceMail.query.filter_by(domain=session['context']).all()

            for voice_mail in voice_mails:
                received = time.strftime("%a, %d %b %Y %H:%M", time.localtime(voice_mail.created_epoch))
                name = voice_mail.cid_number[len(voice_mail.cid_number)-10:]
                fname = voice_mail.file_path.split("/")[len(voice_mail.file_path.split("/"))-1]
                for x in range(1,5):
                    path.append(voice_mail.file_path.split("/")[len(voice_mail.file_path.split("/"))-i])
                    i=i-1
                i = 4

                fpath = "/"+"/".join(path)
                path = []
                items.append({'name': name, 'to': voice_mail.username, 'received': received, 'path': fpath, 'size': voice_mail.message_len})

            db.remove()
            return {'identifier': 'path', 'label': 'name', 'items': items}

        except Exception, e:
            return {'identifier': 'path', 'label': 'name', 'items': [], 'is_error': True, 'messages': str(e)}

    @restrict("POST")
    @authorize(logged_in)
    def delete_voicemail(self, **kw):

        path = request.params['data']
        file_name = path.split("/")[len(path.split("/"))-1]
        uuid = file_name.split("_")[1].split(".")[0].strip()

        try:
            VoiceMail.query.filter(VoiceMail.uuid==uuid).filter(VoiceMail.username==session['ext']).delete()
            dir = fs_vm_dir+"/"+session['context']+"/"+session['ext']
            os.remove(os.path.join(dir, file_name))
        except:
            return "Error: Virtual Extension voicemail can be deleted by dialing * plus extension from a registered endpoint."

        return "Deleted voicemail."

    @authorize(logged_in)
    @jsonify
    def cdr(self):
        items=[]
        try:
            for cdr in PbxCdr.query.filter_by(context=session['context']).order_by(desc(PbxCdr.id)).all():
                num = cdr.caller_id_number if len(cdr.caller_id_number)<=10 else cdr.caller_id_number[len(cdr.caller_id_number)-10:]
                items.append({'id': cdr.id, 'caller_id_name': cdr.caller_id_name, 'caller_id_number': num,
                              'destination_number': cdr.destination_number, 'start_stamp': fix_date(cdr.start_stamp), 'answer_stamp': fix_date(cdr.answer_stamp),
                              'end_stamp': fix_date(cdr.end_stamp), 'duration': cdr.duration, 'billsec': cdr.billsec, 'hangup_cause': cdr.hangup_cause})
            db.remove()

            return {'identifier': 'id', 'label': 'caller_id_number', 'items': items}

        except Exception, e:
            return {'identifier': 'path', 'label': 'caller_id_number', 'items': [], 'is_error': True, 'messages': str(e)}

    @authorize(logged_in)
    @jsonify
    def cdr_summary(self):
        items=[]
        sdate = request.params.get("sdate", 'TIMESTAMP')
        edate = request.params.get("edate", 'CURRENT_TIMESTAMP')

        try:

            sdate = "TIMESTAMP '"+sdate+"'" if sdate != 'TIMESTAMP' else "CURRENT_TIMESTAMP - INTERVAL '1 MONTH'"
            edate = "TIMESTAMP '"+edate+"' + interval '1 day'" if edate != 'CURRENT_TIMESTAMP' else 'CURRENT_TIMESTAMP'

            for row in db.execute("SELECT * "
                                  "FROM cdr "
                                  "WHERE customer_id = :customer_id "
                                  "AND cdr.start_stamp > "+sdate+" AND cdr.end_stamp < "+edate+" "
                                  "ORDER BY start_stamp DESC", {'customer_id': str(session['customer_id'])}).fetchall():

                num = row.caller_id_number if len(row.caller_id_number)<=10 else row.caller_id_number[len(row.caller_id_number)-10:]
                items.append({'id': row.id, 'caller_id_name': row.caller_id_name, 'caller_id_number': num,
                              'destination_number': row.destination_number, 'start_stamp': fix_date(row.start_stamp), 'answer_stamp': fix_date(row.answer_stamp),
                              'end_stamp': fix_date(row.end_stamp), 'duration': row.duration, 'billsec':row.billsec, 'hangup_cause': row.hangup_cause})

            db.remove()
            return {'identifier': 'id', 'label': 'caller_id_number', 'items': items}

        except Exception,e:
            return {'identifier': 'id', 'label': 'caller_id_number', 'items': [], 'is_error': True, 'messages': str(e)}

    @authorize(logged_in)
    @jsonify
    def cdr_ext_summary(self):
        items=[]
        try:
            sdate = request.params.get("sdate", 'TIMESTAMP')
            edate = request.params.get("edate", 'CURRENT_TIMESTAMP')

            sdate = "TIMESTAMP '"+sdate+"'" if sdate != 'TIMESTAMP' else "TIMESTAMP '"+datetime.today().strftime("%m/%d/%Y 12:00:00 AM")+"'"
            edate = "TIMESTAMP '"+edate+"' + interval '1 day'" if edate != 'CURRENT_TIMESTAMP' else 'CURRENT_TIMESTAMP'

            for row in db.execute("SELECT DISTINCT users.id, users.first_name ||' '|| users.last_name AS agent, users.portal_extension as extension, "
                                  "(SELECT COUNT(uuid) FROM cdr WHERE (cdr.caller_id_number = users.portal_extension or cdr.destination_number = users.portal_extension) "
                                  "AND cdr.start_stamp > "+sdate+" AND cdr.end_stamp < "+edate+" AND call_direction = 'inbound' AND cdr.context = customers.context) AS call_count_in, "
                                  "(SELECT COUNT(uuid) FROM cdr WHERE (cdr.caller_id_number = users.portal_extension or cdr.destination_number = users.portal_extension) "
                                  "AND cdr.start_stamp > "+sdate+" AND cdr.end_stamp < "+edate+" AND call_direction = 'outbound' AND cdr.context =  customers.context) AS call_count_out, "
                                  "(SELECT coalesce(sum(billsec),0) FROM cdr WHERE  (cdr.caller_id_number = users.portal_extension or cdr.destination_number = users.portal_extension) "
                                  "AND cdr.start_stamp > "+sdate+" AND cdr.end_stamp < "+edate+" AND call_direction = 'inbound' AND cdr.context =  customers.context) AS time_on_call_in, "
                                  "(SELECT coalesce(sum(billsec),0) FROM cdr WHERE  (cdr.caller_id_number = users.portal_extension or cdr.destination_number = users.portal_extension) "
                                  "AND cdr.start_stamp > "+sdate+" AND cdr.end_stamp < "+edate+" AND call_direction = 'outbound' AND cdr.context =  customers.context) AS time_on_call_out "
                                  "FROM users "
                                  "INNER JOIN customers ON customers.id = users.customer_id "
                                  "WHERE customers.id = :customer_id "
                                  "ORDER BY extension", {'customer_id': session['customer_id']}).fetchall():

                m, s = divmod(row.time_on_call_in, 60)
                h, m = divmod(m, 60)
                toci = "%dh:%02dm:%02ds" % (h, m, s)

                m, s = divmod(row.time_on_call_out, 60)
                h, m = divmod(m, 60)
                toco = "%dh:%02dm:%02ds" % (h, m, s)

                items.append({'id': row.id, 'agent': row.agent, 'extension': row.extension, 'call_count_in': row.call_count_in,
                              'qstring': '?ext='+row.extension+'&sdate='+request.params.get("sdate", 'TIMESTAMP')+'&edate='+request.params.get("edate", 'CURRENT_TIMESTAMP'),
                              'call_count_out': row.call_count_out, 'time_on_call_in': toci, 'time_on_call_out': toco,
                              'from': request.params.get("sdate", 'TIMESTAMP') if request.params.get("sdate", 'TIMESTAMP') != 'TIMESTAMP' else datetime.today().strftime("%m/%d/%Y"),
                              'to': request.params.get("edate", 'CURRENT_TIMESTAMP') if request.params.get("edate", 'CURRENT_TIMESTAMP') != 'CURRENT_TIMESTAMP' else datetime.today().strftime("%m/%d/%Y")})

            db.remove()
            return {'identifier': 'id', 'label': 'agent', 'items': items}

        except Exception, e:
            return {'identifier': 'id', 'label': 'agent', 'items': [], 'is_error': True, 'messages': str(e)}

    @jsonify
    def cdr_ext(self):
        items=[]

        sdate = request.params.get("sdate", 'TIMESTAMP')
        edate = request.params.get("edate", 'CURRENT_TIMESTAMP')

        try:

            ext = request.params.get("ext")

            sdate = "TIMESTAMP '"+sdate+"'" if sdate != 'TIMESTAMP' else "TIMESTAMP '"+datetime.today().strftime("%m/%d/%Y 12:00:00 AM")+"'"
            edate = "TIMESTAMP '"+edate+"' + interval '1 day'" if edate != 'CURRENT_TIMESTAMP' else 'CURRENT_TIMESTAMP'

            for row in db.execute("SELECT  cdr.id AS id, caller_id_name, caller_id_number, destination_number, start_stamp, answer_stamp, "
                                  "end_stamp, duration, billsec, hangup_cause "
                                  "FROM cdr "
                                  "INNER JOIN customers ON cdr.context = customers.context "
                                  "WHERE customers.id = :customer_id "
                                  "AND cdr.start_stamp > "+sdate+" AND cdr.end_stamp < "+edate+" "
                                  "AND cdr.call_direction IS NOT NULL "
                                  "AND (cdr.caller_id_number = :extension or cdr.destination_number = :extension) "
                                  "ORDER BY id", {'customer_id': session['customer_id'], 'extension': ext}).fetchall():

                num = row.caller_id_number if len(row.caller_id_number)<=10 else row.caller_id_number[len(row.caller_id_number)-10:]

                items.append({'id': row.id, 'caller_id_name': row.caller_id_name, 'caller_id_number': num,
                              'destination_number': row.destination_number, 'start_stamp': fix_date(row.start_stamp), 'answer_stamp': fix_date(row.answer_stamp),
                              'end_stamp': fix_date(row.end_stamp), 'duration': row.duration, 'billsec':row.billsec, 'hangup_cause': row.hangup_cause})

            db.remove()
            return {'identifier': 'id', 'label': 'caller_id_number', 'items': items}
        except  e:
            return {'identifier': 'id', 'label': 'caller_id_number', 'items': [], 'is_error': True, 'messages': str(e)}

    @authorize(logged_in)
    def cdr_ext_download(self):
        items=[]

        start = request.params.get("sdate")
        end = request.params.get("edate")

        sdate = request.params.get("sdate", 'TIMESTAMP')
        edate = request.params.get("edate", 'CURRENT_TIMESTAMP')

        ext = request.params.get("ext")

        sdate = "TIMESTAMP '"+sdate+"'" if sdate != 'TIMESTAMP' else "TIMESTAMP '"+datetime.today().strftime("%m/%d/%Y 12:00:00 AM")+"'"
        edate = "TIMESTAMP '"+edate+"' + interval '1 day'" if edate != 'CURRENT_TIMESTAMP' else 'CURRENT_TIMESTAMP'

        for row in db.execute("SELECT  cdr.id AS id, caller_id_name, caller_id_number, destination_number, start_stamp, answer_stamp, "
                              "end_stamp, duration, billsec, hangup_cause "
                              "FROM cdr "
                              "INNER JOIN customers ON cdr.context = customers.context "
                              "WHERE customers.id = :customer_id "
                              "AND cdr.start_stamp > "+sdate+" AND cdr.end_stamp < "+edate+" "
                              "AND cdr.call_direction IS NOT NULL "
                              "AND (cdr.caller_id_number = :extension or cdr.destination_number = :extension) "
                              "ORDER BY id", {'customer_id': session['customer_id'], 'extension': ext}).fetchall():

            num = row.caller_id_number if len(row.caller_id_number)<=10 else row.caller_id_number[len(row.caller_id_number)-10:]

            items.append({'id': row.id, 'caller_id_name': row.caller_id_name, 'caller_id_number': num,
                          'destination_number': row.destination_number, 'start_stamp': fix_date(row.start_stamp), 'answer_stamp': fix_date(row.answer_stamp),
                          'end_stamp': fix_date(row.end_stamp), 'duration': row.duration, 'billsec':row.billsec, 'hangup_cause': row.hangup_cause})

        db.remove()

        f = open("/tmp/Report_ext"+ext+".csv", "wb+")
        csv_file = csv.writer(f)

        #f=csv.writer(open("/tmp/Report_ext"+ext+".csv",'wb+'))
        csv_file.writerow(["Name","Number","Destination","Start Time","End Time", "Duration Seconds","Hangup Cause"])

        for csv_items in items:
            csv_file.writerow([csv_items['caller_id_name'], csv_items['caller_id_number'], csv_items['destination_number'], csv_items['start_stamp'], csv_items['duration'], csv_items['hangup_cause']])

        f.close()

        size = os.path.getsize("/tmp/Report_ext"+ext+".csv")

        response = make_file_response("/tmp/Report_ext"+ext+".csv")
        response.headers = [("Content-type", "application/octet-stream"),
            ("Content-Disposition", "attachment; filename="+"Report_ext"+ext+".csv"),
            ("Content-length", str(size)),]

        return response(request.environ, self.start_response)


    @authorize(logged_in)
    def customer_by_id(self, **kw):
        items=[]
        row = Customer.query.filter(Customer.id==session['customer_id']).first()
        items.append({'id': row.id, 'name': row.name, 'email': row.email, 'address': row.address, 'address_2': row.address_2,
                      'city': row.city, 'state': row.state, 'zip': row.zip,
                      'tel': row.tel, 'url': row.url, 'active': row.active, 'context': row.context, 'has_crm': row.has_crm,
                      'has_call_center': row.has_call_center, 'contact_name': row.contact_name, 'contact_phone': row.contact_phone,
                      'contact_mobile': row.contact_mobile, 'contact_title': row.contact_title, 'contact_email': row.contact_email, 'notes': row.notes})

        out = dict({'identifier': 'id', 'label': 'name', 'items': items})
        response = make_response(out)
        response.headers = [("Content-type", 'application/json; charset=UTF-8'),]

        return response(request.environ, self.start_response)

    @authorize(logged_in)
    def edit_customer(self):
        schema = CustomerForm()

        try:
            form_result = schema.to_python(request.params)
            customer = Customer.query.filter(Customer.id==session['customer_id']).first()
            customer.tel = form_result.get('tel')
            customer.address = form_result.get('address')
            customer.address_2 = form_result.get('address_2')
            customer.city = form_result.get('city')
            customer.state = form_result.get('state')
            customer.zip = form_result.get('zip')
            customer.url = form_result.get('url')
            customer.email = form_result.get('email')
            customer.contact_name = form_result.get('contact_name')
            customer.contact_phone = form_result.get('contact_phone')
            customer.contact_mobile = form_result.get('contact_mobile')
            customer.contact_title = form_result.get('contact_title')
            customer.contact_email = form_result.get('contact_email')

            db.commit(); db.flush()

        except validators.Invalid, error:
            db.remove()
            return 'Error: %s' % error

        return "Successfully edited customer."

    @jsonify
    @authorize(logged_in)
    def avail_findme_endpoints(self):
        items=[]
        for row in PbxEndpoint.query.filter_by(user_context=session['context']).order_by(PbxEndpoint.auth_id).all():
            if PbxFindMeRoute.query.filter_by(pbx_endpoint_id=row.id).count()>0:
                continue
            items.append({'id': row.id, 'auth_id': row.auth_id})
        db.remove()

        out = dict({'identifier': 'id', 'label': 'auth_id', 'items': items})
        response = make_response(out)
        response.headers = [("Content-type", 'application/json; charset=UTF-8'),]

        return response(request.environ, self.start_response)

    @authorize(logged_in)
    def inuse_findme_endpoints(self):
        items=[]
        for row in db.query(PbxFindMeRoute.id, PbxEndpoint.auth_id)\
        .select_from(join(PbxFindMeRoute, PbxEndpoint, PbxEndpoint.pbx_find_me))\
        .filter(PbxEndpoint.user_context==session['context']).all():
            items.append({'id': row.id, 'auth_id': row.auth_id})

        db.remove()

        out = dict({'identifier': 'id', 'label': 'auth_id', 'items': items})
        response = make_response(out)
        response.headers = [("Content-type", 'application/json; charset=UTF-8'),]

        return response(request.environ, self.start_response)

    @authorize(logged_in)
    def routes(self):
        items=[]
        for row in db.execute("SELECT sr.id, sr.name AS data, sr.pbx_to_id AS to_id, sr.pbx_route_type_id AS type_id, srt.name|| ': ' ||sr.name AS name "
                              "FROM pbx_routes sr "
                              "INNER JOIN pbx_route_types srt ON sr.pbx_route_type_id = srt.id "
                              "WHERE sr.context = :context", {'context': session['context']}):
            items.append({'id': row.id, 'data': row.data, 'to_id': row.to_id, 'type_id': row.type_id, 'name': row.name})
        db.remove()

        out = dict({'identifier': 'id', 'label': 'name', 'items': items})
        response = make_response(out)
        response.headers = [("Content-type", 'application/json; charset=UTF-8'),]

        return response(request.environ, self.start_response)

    @jsonify
    @authorize(logged_in)
    def route_id_names(self):
        return db.query(PbxRoute.name, PbxRoute.id).filter_by(context=session['context']).all()

    @jsonify
    @authorize(logged_in)
    def route_ids(self):
        names=[]
        ids=[]

        for r in db.query(PbxRoute.name, PbxRoute.id).filter_by(context=session['context']).order_by(PbxRoute.name).all():
            names.append(r.name)
            ids.append(r.id)

        return dict({'names': names, 'ids': ids})


    @authorize(logged_in)
    def call_stats(self):
        items=[]
        volume=[]
        ttime=[]
        minimumt = 0
        maximumt = 0
        minimumv = 0
        maximumv = 10
        for row in User.query.filter(User.customer_id==session['customer_id']).all():
            if not len(row.portal_extension):
                continue
            else:
                extension = row.portal_extension
            vol =  get_volume(extension)
            tt = get_talk_time(extension)
            if vol > maximumv:
                maximumv = vol
            if tt > maximumt:
                maximumt = tt
            volume.append({'x': row.first_name+' '+row.last_name, 'y': vol})
            ttime.append({'x': row.first_name+' '+row.last_name, 'y': tt})
            items.append({'id': row.id, 'extension': extension, 'name': row.first_name+' '+row.last_name, 'volume': vol, 'talk_time': tt})

        db.remove()

        out = dict({'identifier': 'id', 'label': 'name', 'items': items, 'mint': minimumt,
                    'maxt': maximumt, 'minv': minimumv, 'maxv': maximumv, 'volume': volume, 'talk_time': ttime})
        response = make_response(out)
        response.headers = [("Content-type", 'application/json; charset=UTF-8'),]

        return response(request.environ, self.start_response)

    @authorize(logged_in)
    def get_find_me_edit(self, id, **kw):
        c.findme = db.query(PbxFindMeRoute.id,PbxFindMeRoute.ring_strategy, PbxFindMeRoute.destination_1, PbxFindMeRoute.destination_2,\
            PbxFindMeRoute.destination_3, PbxFindMeRoute.destination_4, PbxEndpoint.auth_id)\
                .select_from(join(PbxFindMeRoute, PbxEndpoint, PbxEndpoint.pbx_find_me))\
                .filter(PbxEndpoint.user_context==session['context'])\
                .filter_by(id=id).first()
        db.remove()
        return render('find_me_edit.html')

    @authorize(credential('pbx_admin'))
    def permissions(self, id, **kw):
        c.findme = db.query(PbxFindMeRoute.id,PbxFindMeRoute.ring_strategy, PbxFindMeRoute.destination_1, PbxFindMeRoute.destination_2,\
            PbxFindMeRoute.destination_3, PbxFindMeRoute.destination_4, PbxEndpoint.auth_id)\
                .select_from(join(PbxFindMeRoute, PbxEndpoint, PbxEndpoint.pbx_find_me))\
                .filter(PbxEndpoint.user_context==session['context'])\
                .filter_by(id=id).first()
        db.remove()
        return render('find_me_edit.html')

    @authorize(logged_in)
    def names_user_ids(self):
        names=[]
        user_ids=[]
        for row in User.query.filter_by(customer_id=session['customer_id']).all():
            names.append(row.first_name+' '+row.last_name)
            user_ids.append(row.id)

        db.remove()

        out = dict({'names': names, 'user_ids': user_ids})
        response = make_response(out)
        response.headers = [("Content-type", 'application/json; charset=UTF-8'),]

        return response(request.environ, self.start_response)

    @authorize(logged_in)
    def destinations(self):
        items=[]
        for row in PbxEndpoint.query.filter_by(user_context=session['context']).all():
            items.append({'id': row.id, 'ext': row.auth_id})

        db.remove()

        out = dict({'identifier': 'ext', 'label': 'ext', 'items': items})
        response = make_response(out)
        response.headers = [("Content-type", 'application/json; charset=UTF-8'),]

        return response(request.environ, self.start_response)

    @authorize(logged_in)
    def device_store(self):
        items=[]
        for row in db.query(PbxDeviceManufacturer.id, PbxDeviceManufacturer.name,  PbxDeviceType.model,
            PbxDeviceType.id).join(PbxDeviceType).order_by(PbxDeviceManufacturer.name).all():
            items.append({'id': row[0], 'manufacturer': row[1], 'model': row[2], 'name':  row[1]+ ': '+row[2], 'device_type_id': row[3]})

        db.remove()

        out = dict({'identifier': 'device_type_id', 'label': 'name', 'items': items})
        response = make_response(out)
        response.headers = [("Content-type", 'application/json; charset=UTF-8'),]

        return response(request.environ, self.start_response)

    @authorize(logged_in)
    def login_ext(self, id):
        items=[]
        for row in PbxEndpoint.query.filter_by(user_context=session['context']).\
        filter_by(user_id=id).order_by(PbxEndpoint.auth_id).all():
            items.append({'id': row.id, 'extension': row.auth_id})
        db.remove()

        out = dict({'identifier': 'extension', 'label': 'extension', 'items': items})
        response = make_response(out)
        response.headers = [("Content-type", 'application/json; charset=UTF-8'),]

        return response(request.environ, self.start_response)

    @authorize(logged_in)
    def help(self, id, **kw):
        help = PbxHelp.query.filter(PbxHelp.category_id==id).first()

        if help:
            data = help.data
        else:
            data = "No help to display in this category."

        db.remove()

        out = dict({'help': data})
        response = make_response(out)
        response.headers = [("Content-type", 'application/json; charset=UTF-8'),]

        return response(request.environ, self.start_response)

    @authorize(logged_in)
    def ext_recordings2(self):
        files = []

        dir = fs_vm_dir+session['context']+"/extension-recordings/"

        try:
            for i in os.listdir(dir):
                id = i.split("_")[1].split("_")[0].strip()
                direction = i.split("_")[2]
                ext = i.split("_")[0]
                row = PbxCdr.query.filter(PbxCdr.uuid==id).first()
                if not row:
                    continue
                path = dir+"/"+i
                tpath = "/vm/"+session['context']+"/extension-recordings/"+i
                received = str(modification_date(path)).strip("\"")
                fsize = str(os.path.getsize(path))
                caller = row.caller_id_number[len(row.caller_id_number)-10:]
                dest = row.destination_number[len(row.destination_number)-10 if len(row.destination_number) > 10 else 0:]
                files.append({'name': caller, 'dest': dest, 'path': tpath, 'received': received, 'size': fsize, 'extension': ext, 'id': id, 'direction': direction})
        except Exception, e:
            raise

        out = dict({'identifier': 'id', 'label': 'name', 'items': files})
        response = make_response(out)
        response.headers = [("Content-type", 'application/json; charset=UTF-8'),]

        return response(request.environ, self.start_response)

    @authorize(logged_in)
    def ext_recordings(self):
        files = []

        dir = fs_vm_dir+session['context']+"/extension-recordings/"

        try:
            for i in os.listdir(dir):
                id = i.split("_")[1].split("_")[0].strip()
                direction = i.split("_")[2]
                ext = i.split("_")[0]
                row = PbxCdr.query.filter(PbxCdr.uuid==id).first()
                if not row:
                    continue
                path = dir+"/"+i
                tpath = "/vm/"+session['context']+"/extension-recordings/"+i
                received = str(modification_date(path)).strip("\"")
                fsize = str(os.path.getsize(path))
                caller = row.caller_id_number[len(row.caller_id_number)-10:]
                dest = row.destination_number[len(row.destination_number)-10 if len(row.destination_number) > 10 else 0:]
                files.append({'name': caller, 'dest': dest, 'path': tpath, 'received': received, 'size': fsize, 'extension': ext, 'id': id, 'direction': direction})
        except Exception, e:
            raise

        out = dict({'identifier': 'id', 'label': 'name', 'items': files})
        response = make_response(out)
        response.headers = [("Content-type", 'application/json; charset=UTF-8'),]

        return response(request.environ, self.start_response)

    @authorize(logged_in)
    def active_tickets(self):
        items=[]
        for row in Ticket.query.filter_by(customer_id=session['customer_id']).filter(Ticket.ticket_status_id!=4).all():
            items.append({'id': row.id, 'customer_id': row.customer_id, 'opened_by': row.opened_by,
                          'status': row.ticket_status_id, 'priority': row.ticket_priority_id,
                          'type': row.ticket_type_id, 'created': row.created.strftime("%m/%d/%Y %I:%M:%S %p"),
                          'expected_resolve_date': row.expected_resolve_date.strftime("%m/%d/%Y %I:%M:%S %p"),
                          'subject': row.subject, 'description': row.description})

        db.remove()

        out = dict({'identifier': 'id', 'label': 'id', 'items': items})
        response = make_response(out)
        response.headers = [("Content-type", 'application/json; charset=UTF-8'),]

        return response(request.environ, self.start_response)

    @authorize(logged_in)
    def closed_tickets(self):
        items=[]
        for row in Ticket.query.filter_by(customer_id=session['customer_id']).filter(Ticket.ticket_status_id==4).all():
            items.append({'id': row.id, 'customer_id': row.customer_id, 'opened_by': row.opened_by,
                          'status': row.ticket_status_id, 'priority': row.ticket_priority_id,
                          'type': row.ticket_type_id, 'created': row.created.strftime("%m/%d/%Y %I:%M:%S %p"),
                          'expected_resolve_date': row.expected_resolve_date.strftime("%m/%d/%Y %I:%M:%S %p"),
                          'subject': row.subject, 'description': row.description})

        db.remove()

        out = dict({'identifier': 'id', 'label': 'id', 'items': items})
        response = make_response(out)
        response.headers = [("Content-type", 'application/json; charset=UTF-8'),]

        return response(request.environ, self.start_response)


    @authorize(logged_in)
    def internal_tickets(self):
        items=[]
        for row in Ticket.query.filter_by(customer_id=session['customer_id']).filter(Ticket.ticket_status_id==7).all():
            items.append({'id': row.id, 'customer_id': row.customer_id, 'opened_by': row.opened_by,
                          'status': row.ticket_status_id, 'priority': row.ticket_priority_id,
                          'type': row.ticket_type_id, 'created': row.created.strftime("%m/%d/%Y %I:%M:%S %p"),
                          'expected_resolve_date': row.expected_resolve_date.strftime("%m/%d/%Y %I:%M:%S %p"),
                          'subject': row.subject, 'description': row.description})

        db.remove()

        out = dict({'identifier': 'id', 'label': 'id', 'items': items})
        response = make_response(out)
        response.headers = [("Content-type", 'application/json; charset=UTF-8'),]

        return response(request.environ, self.start_response)


    @authorize(logged_in)
    def ticket_data(self):
        ticket_status_id =[]
        ticket_status_name =[]
        ticket_type_id = []
        ticket_type_name = []
        ticket_priority_id = []
        ticket_priority_name = []
        opened_by_id = []
        opened_by_name = []

        for row in TicketStatus.query.all():
            ticket_status_id.append(row.id)
            ticket_status_name.append(row.name)
        for row in TicketType.query.all():
            ticket_type_id.append(row.id)
            ticket_type_name.append(row.name)
        for row in TicketPriority.query.all():
            ticket_priority_id.append(row.id)
            ticket_priority_name.append(row.name)
        for row in User.query.filter_by(customer_id=session['customer_id']).all():
            opened_by_id.append(row.id)
            opened_by_name.append(row.first_name+' '+row.last_name)

        db.remove()

        out = dict({'ticket_status_names': ticket_status_name, 'ticket_status_ids': ticket_status_id,
                    'ticket_type_names': ticket_type_name, 'ticket_type_ids': ticket_type_id,
                    'ticket_priority_names': ticket_priority_name, 'ticket_priority_ids': ticket_priority_id,
                    'opened_by_names': opened_by_name, 'opened_by_ids': opened_by_id})

        response = make_response(out)
        response.headers = [("Content-type", 'application/json; charset=UTF-8'),]

        return response(request.environ, self.start_response)

    @authorize(logged_in)
    def ticket_types(self):
        items=[]
        for row in TicketType.query.all():
            items.append({'id': row.id, 'name': row.name, 'description': row.description})

        db.remove()

        out = dict({'identifier': 'id', 'label': 'name', 'items': items})
        response = make_response(out)
        response.headers = [("Content-type", 'application/json; charset=UTF-8'),]

        return response(request.environ, self.start_response)

    @authorize(logged_in)
    def ticket_statuses(self):
        items=[]
        for row in TicketStatus.query.all():
            items.append({'id': row.id, 'name': row.name, 'description': row.description})

        db.remove()

        out = dict({'identifier': 'id', 'label': 'name', 'items': items})
        response = make_response(out)
        response.headers = [("Content-type", 'application/json; charset=UTF-8'),]

        return response(request.environ, self.start_response)

    @authorize(logged_in)
    def ticket_priorities(self):
        items=[]
        for row in TicketPriority.query.all():
            items.append({'id': row.id, 'name': row.name, 'description': row.description})

        db.remove()

        out = dict({'identifier': 'id', 'label': 'name', 'items': items})
        response = make_response(out)
        response.headers = [("Content-type", 'application/json; charset=UTF-8'),]

        return response(request.environ, self.start_response)

    @authorize(logged_in)
    def ticket_add(self, **kw):
        schema = TicketForm()
        try:
            form_result = schema.to_python(request.params)
            t = Ticket()
            t.subject = form_result.get('subject')
            t.description = form_result.get('description')
            t.customer_id = session['customer_id']
            t.opened_by = form_result.get('user_id')
            t.ticket_status_id = form_result.get('status_id')
            t.ticket_priority_id = form_result.get('priority_id')
            t.ticket_type_id = form_result.get('type_id')
            t.expected_resolution_date = form_result.get('expected_resolution_date')

            db.add(t)
            db.commit(); db.flush()

        except validators.Invalid, error:
            db.remove()
            return 'Validation Error: %s' % error

        db.remove()
        return "Successfully added ticket."

    @authorize(logged_in)
    def update_ticket_grid(self, **kw):

        w = loads(urllib.unquote_plus(request.params.get("data")))

        for i in w['modified']:
            ticket = Ticket.query.filter_by(id=i['id']).first()
            ticket.ticket_status_id = int(i['status'])
            ticket.ticket_type_id = int(i['type'])
            ticket.ticket_priority_id = int(i['priority'])

            db.commit(); db.flush()
            db.remove()

        return "Successfully updated ticket."

    @authorize(logged_in)
    def ticket_view_by_id(self, id):
        items=[]
        notes=[]
        for row in Ticket.query.filter_by(customer_id=session['customer_id']).filter(Ticket.id==id).all():
            for note in TicketNote.query.filter_by(ticket_id=row.id).all():
                notes.append({'id': note.id, 'ticket_id': note.ticket_id, 'user_id': note.user_id,
                              'created': note.created.strftime("%m/%d/%Y %I:%M:%S %p"), 'subject': note.subject,
                              'description': note.description})



            items.append({'id': row.id, 'customer_id': row.customer_id, 'opened_by': row.opened_by,
                          'status': row.ticket_status_id, 'priority': row.ticket_priority_id,
                          'type': row.ticket_type_id, 'created': row.created.strftime("%m/%d/%Y %I:%M:%S %p"),
                          'expected_resolve_date': row.expected_resolve_date.strftime("%m/%d/%Y %I:%M:%S %p"),
                          'subject': row.subject, 'description': row.description, 'notes': notes})


        out = dict({'identifier': 'id', 'label': 'id', 'items': items})
        response = make_response(out)
        response.headers = [("Content-type", 'application/json; charset=UTF-8'),]

        return response(request.environ, self.start_response)

    @authorize(logged_in)
    def ticket_notes_by_id(self, id):
        items=[]
        for note in TicketNote.query.filter_by(ticket_id=id).all():
            items.append({'id': note.id, 'ticket_id': note.ticket_id, 'user_id': note.user_id,
                          'created': note.created.strftime("%m/%d/%Y %I:%M:%S %p"), 'subject': note.subject,
                          'description': note.description})

        out = dict({'identifier': 'id', 'label': 'subject', 'items': items})
        response = make_response(out)
        response.headers = [("Content-type", 'application/json; charset=UTF-8'),]

        return response(request.environ, self.start_response)

    @authorize(logged_in)
    def add_ticket_note(self, **kw):
        schema = TicketNoteForm()
        try:
            form_result = schema.to_python(request.params)
            t = TicketNote()
            t.ticket_id = form_result.get('ticket_note_id')
            t.subject = form_result.get('ticket_subject')
            t.description = form_result.get('ticket_note')
            t.user_id = form_result.get('user_id')

            db.add(t)
            db.commit(); db.flush()

        except validators.Invalid, error:
            db.remove()
            return 'Validation Error: %s' % error

        db.remove()
        return "Successfully added ticket note."