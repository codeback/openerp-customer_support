# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution   
#    Copyright (C) 2013 Codeback Software S.L. (www.codeback.es). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp.osv import fields,osv
from openerp.tools.translate import _

from datetime import datetime, timedelta
from decimal import Decimal
import pdb
import tor
import json
import urllib
import urllib2

class support_ticket(osv.osv):   
    _name = "support.ticket"
    _columns = {
        'email': fields.char('E-mail', size=64), 
        'name': fields.char('Name', size=64), 
        'subject': fields.char('Subject', size=512),
        'body': fields.text('Body'),
        'html': fields.selection([('true','True'),('false','False')], 'HTML Ticket'),
        'date': fields.datetime('Date'), #Coger de OpenERP
        'labels': fields.selection([('not urgent','Low Priority'),('normal','Medium Priority'), ('urgent','High Priority')],'Ticket Priority'),
        'status': fields.selection([(1,'Open'),(2,'In Progress'),(3,'Closed'),(4,'Pending')],'Ticket Status'),
        'identifier': fields.integer('Identifier'),
        }  

    def run_scheduler(self, cr, uid, args, context=None):
        """ Update from scheduler"""   
        self.update_tickets(cr, uid, args, context=context)
        return True

    def create(self, cr, user, vals, context=None):
        
        # Leer datos de configutacion
        config = self._get_config_data(cr,user)

        if vals:
            #API_KEY = "6KzviBIGDTbYPjtglKqThZaXdhMc2md"
            #PROJECT_DOMAIN = "codeback"

            api = tor.TorApi(config['tor_api_key'], config['tor_domain'])
            # Se rellena el contenido del ticket
            ticket = {}
            if self._get_user_email(cr, user, context=None):
                ticket["email"] = self._get_user_email(cr, user, context=None)
            else:
                raise osv.except_osv(_('Invalid email!'), _('Please, set your email address in your user settings page.'))
            
            ticket["from_name"] = self._get_user(cr, user, context=None)
            ticket["subject"] = vals['subject']            
            ticket["body"] = vals['body']
            ticket["html"] = 'False' # Correo en texto plano por defecto
            ticket["date"] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ticket["labels"] = [config['company'],vals['labels']]
            pdb.set_trace()
            ticket["status"] = 4
            vals['date'] = datetime.now()
            vals['status'] = 4

            # Descomentar estas líneas para posibilitar incluir adjuntos
            # poster lib required (http://pypi.python.org/pypi/poster/)
            # ticket["attachment"] = "attachment.txt"

            # Se crea el ticket
            ticket_result = api.new_ticket(ticket)

            # Se asignan los valores que no se cogen del formulario para que se muestren en la lista OpenERP
            vals['identifier']=ticket_result["id"]
            vals['name'] = self._get_user(cr, user, context=None)
            vals['email'] = self._get_user_email(cr, user, context=None)
                          
        return super(support_ticket, self).create(cr, user, vals, context)
        

    def update_tickets(self, cr, uid, vals, context=None):

        config = self._get_config_data(cr,uid)
        # Obtenemos la lista de tickets no cerrados en OpenERP
        oe_ticket_list = self.get_open_tickets(cr, uid)

        # Obtenemos la información de los tickets del sistema remoto        
        #API_KEY = "6KzviBIGDTbYPjtglKqThZaXdhMc2md"
        #PROJECT_DOMAIN = "codeback"
        api = tor.TorApi(config['tor_api_key'], config['tor_domain'])      
        tor_ticket_list = api.get_tickets(1,100)   
        
        # Actualizamos el estado de los tickets
        for ticket in oe_ticket_list:            
            for remote_ticket in tor_ticket_list['tickets']:
                if ticket.identifier == int(remote_ticket['id']):                    
                    # Actualizamos el registro con el status recuperado
                    current_status = int(remote_ticket['status'])
                    record = {                        
                        'status': current_status + 1, # Ajuste del índice para evitar el problema con el id=0
                    }                    
                    self.write(cr, uid, [ticket.id], record, context)                                   
                                   
        return True

    def get_open_tickets(self, cr, uid):
        open_tickets = self._get_objects(cr, uid, 'support.ticket')
        return [st for st in open_tickets if st.status!='2']

    def _get_objects(self, cr, uid, name, args=[], ids=None):   
        """
        Obtiene los objetos del modelo 'name'
        """    
        obj = self.pool.get(name)
        if not ids:
            ids = obj.search(cr, uid, args)
        return obj.browse(cr, uid, ids)

    def _get_user_email(self, cr, uid, context=None):
        res={}
        return self.pool.get('res.users').browse(cr, uid, uid).user_email

    def _get_user(self, cr, uid, context=None):
        res={}
        return self.pool.get('res.users').browse(cr, uid, uid).name    

    def _get_config_data(self, cr, uid):
        """
        Lee los datos de configutacion
        """

        model_conf = self.pool.get('customer.support.settings')
        args = [('selected', '=', True)]    
        ids = model_conf.search(cr, uid, args)
        config = model_conf.browse(cr, uid, ids[0])

        return {
            'tor_api_key': config.tor_api_key,
            'tor_domain': config.tor_domain,
            'company': config.company
        }
     
support_ticket()

class customer_support_settings(osv.osv):
    _name = "customer.support.settings"

    _columns = {
        'name': fields.char('Name', size=64, required=True),
        'tor_api_key' : fields.char('ToR API Key', size=64, required=True),
        'tor_domain' : fields.char('ToR Domain', size=64, required=True),
        'company' : fields.char('Short Company Denomination', size=64, required=True),
        'selected': fields.boolean('Selected'),
    }

customer_support_settings()

class support_ticket_updater(osv.osv_memory):
    _name= "support.ticket.updater"
    _columns = {}

    def run_update_tickets(self, cr, uid, ids, context=None):
        """ Update stock from wizard"""    

        obj = self.pool.get('support.ticket')
        obj.update_tickets(cr, uid, vals=None)
        
        menu_mod = self.pool.get('ir.ui.menu')        
        args = [('name', '=', 'Ticket List')]
        menu_ids = menu_mod.search(cr, uid, args)
        
        return {
            'name': 'Run manually',
            'type': 'ir.actions.client',
            'tag': 'reload',
            'params': {'menu_id': menu_ids[0]},
        }

support_ticket_updater()