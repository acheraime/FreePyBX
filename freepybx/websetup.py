""" This Source Code Form is subject to the terms of the Mozilla Public
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

import logging
import pylons.test
from pylons import config
from freepybx.config.environment import load_environment
from freepybx.model import *

log = logging.getLogger(__name__)


def setup_app(command, conf, vars):
    """Place any commands to setup freepybx here"""
    # Don't reload the app if it was loaded under the testing environment
    if not pylons.test.pylonsapp:
        load_environment(conf.global_conf, conf.local_conf)

    Base.metadata.drop_all(bind=db.bind)
    Base.metadata.create_all(bind=db.bind)

    # Create the tables if they don't already exist        
    # uncomment and adjust for initial setup..
    insert_data()
    
def insert_data():

    route_types = [
        (u'Extension', None),
        (u'Virtual Extension', None),
        (u'Virtual Mailbox', None),
        (u'Group', None),
        (u'IVR', None),
        (u'Time of Day', None),
        (u'Conference Bridge', None),
        (u'Caller ID Route', None),
        (u'DID', None),
        (u'Call Center', None),
        (u'Directory', None),
        (u'Fax', None)
    ]

    for key, value in route_types:
        s = PbxRouteType()
        s.name = key
        s.description = value
        db.add(s)

    # Add initial admin with admin login rights
    admin_user = AdminUser(u'admin@freepybx.org',u'secretpass1',u'Admin',u'User')
    db.add(admin_user)

    admin_group = AdminGroup(u'system_admin',u'System administrators')
    admin_group.admin_users.append(admin_user)
    db.add(admin_group)

    admin_perm = AdminPermission(u'superuser',u'all access')
    admin_perm.admin_groups.append(admin_group)
    db.add(admin_perm)

    pba = Group(u'pbx_admin', u'PBX Admins')
    pba.permissions.append(Permission(u'pbx_admin'))
    db.add(pba)

    pbe = Group(u'pbx_extension', u'PBX Extension Users')
    pbe.permissions.append(Permission(u'pbx_extension'))
    db.add(pbe)

    pbb = Group(u'billing', u'Billing Administrators')
    pbb.permissions.append(Permission(u'pbx_admin'))
    db.add(pbb)

    # Setup the default VoIP services as an example to get you started on the concept.
    db.add(BillingServiceType(u'VoIP Service', u'Voice over Internet Protocol Service'))
    db.add(VoipServiceType(u'VoIP PBX Service', u'Private Branch Exchange Service'))
    db.add(VoipServiceType(u'VoIP Extension Service', u'VoIP Extension'))
    db.add(VoipServiceType(u'VoIP Trunk Service', u'Voip Trunk'))
    db.add(VoipServiceType(u'DID', u'Direct Inward Dial Number'))
    db.add(VoipServiceType(u'8XX', u'8XX Number'))

    db.add(BillingProductType(u'Voip Telephones'))
    db.add(BillingProductType(u'Voip ATA'))

    db.add(BillingServiceFeeType(u'Tax', u'Local taxes'))
    db.add(BillingServiceFeeType(u'USF Fee', u'Local taxes'))

    db.add(ProviderBillingApiType(u'Credit Card Gateway', u'Charge customer card via credit card processing gateway.'))
    db.add(BillingCycleType(u'Monthly', u'Monthly Service'))
    db.add(BillingCycleType(u'Annual', u'Annual Service'))
    db.add(BillingCycleType(u'Prepay Pool', u'Prepay Service Deducted from account funds.'))
    db.add(PaymentType(u'Credit Card Auto Bill', u'Charged credit card via merchant gateway automatically.'))
    db.add(PaymentType(u'Credit Card By Employee', u'Manually charged credit card via merchant gateway by employee.'))

    tp = TicketPriority()
    tp.name = u'Critical'
    tp.description = u'Significant risk of negative financial or public relations impact. Significant systems degradation/loss.'
    db.add(tp)
    db.commit()


    tp = TicketPriority()
    tp.name = u'High'
    tp.description = u'Small risk of negative financial or public relations impact.'
    db.add(tp)
    db.commit()

    tp = TicketPriority()
    tp.name = u'Medium'
    tp.description = u'Verified, but isolated instance.'
    db.add(tp)
    db.commit()

    tp = TicketPriority()
    tp.name = u'Low'
    tp.description = u'Limited, but verified system instance.'
    db.add(tp)
    db.commit()

    tp = TicketStatus()
    tp.name = u'Open'
    tp.description = u'Modified since originally created.'
    db.add(tp)
    db.commit()

    tp = TicketStatus()
    tp.name = u'In Progress'
    tp.description = u'Currently being addressed.'
    db.add(tp)
    db.commit()

    tp = TicketStatus()
    tp.name = u'Closed'
    tp.description = u'Work required has been completed.'
    db.add(tp)
    db.commit()

    tp = TicketType()
    tp.name = u'PBX'
    tp.description = u'Feature not working.'
    db.add(tp)
    db.commit()

    tp = TicketType()
    tp.name = u'Feature Request'
    tp.description = u'New Feature Request.'
    db.add(tp)
    db.commit()

    tp = TicketType()
    tp.name = u'Device Connectivity'
    tp.description = u'Device Not Connecting/Authenticating.'
    db.add(tp)
    db.commit()

    tp = TicketType()
    tp.name = u'Network Related'
    tp.description = u'Not Connecting to switch.'
    db.add(tp)
    db.commit()

    tp = TicketType()
    tp.name = u'Call Detail'
    tp.description = u'Inncorrect Call Detail.'
    db.add(tp)
    db.commit()

    tp = TicketType()
    tp.name = u'Feature Request'
    tp.description = u'New Feature Request.'
    db.add(tp)
    db.commit()