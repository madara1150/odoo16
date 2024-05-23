from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import timedelta

class Property(models.Model):
    # ชื่อ table
    _name = 'property'
    # chat จะ track created เป็น description ==> Property Record created.
    _description = 'Property Record'
    _inherit = ['mail.thread','mail.activity.mixin']

    ref = fields.Char(default='New', readonly=1)
    # ชื่อ column
    name = fields.Char(required=1, default='New', size=50)
    # tracking เหมือนใช้ร่วมกับแชท ทำให้เวลากระทำอะไรจะแสดง chat ออกมา
    description = fields.Text(tracking=1)
    postcode = fields.Char(required=1)
    date_availability = fields.Date(tracking=1)
    expected_selling_date = fields.Date(tracking=1)
    is_late = fields.Boolean()
    # digits ไว้ทำเป็นทศนิยม กรณีนี้คือ ทศนิยม 5 หลัก 0.00000
    expected_price = fields.Float(digits=(0,5))
    # ทำ compute field และ store ไว้ทำเมื่อ ต้องการมี field diff ปกติใส่ compute จะไม่มี fields นี้ใน database
    diff = fields.Float(compute='_compute_diff', store=1)
    selling_price = fields.Float()
    bedrooms = fields.Integer()
    living_area = fields.Integer()
    facades = fields.Integer()
    # สามารถกำหนดสิทธิให้คนเข้าได้ถึง field นี้ได้
    garage = fields.Boolean(groups="practice.property_manager_group")
    garden = fields.Boolean()
    garden_area = fields.Integer()
    # เป็น select
    garden_orientation = fields.Selection([
        ('north','North'), 
        ('south','South'), 
        ('east','East'),
        ('west', 'West')
        ],default='north')
    
    # ทำพวก many to one , one to many
    owner_id = fields.Many2one('owner')
    tag_ids = fields.Many2many('tag')

    #ทำ relation ระหว่าง field ข้าม table
    owner_address = fields.Char(related='owner_id.address', readonly=0, store=1)
    owner_phone = fields.Char(related='owner_id.phone', readonly=0)
    create_time = fields.Datetime(default=fields.Datetime.now())
    next_time = fields.Datetime(compute='_compute_next_time')

    # สร้าง state ทั้งหมดขึ้นมา
    state = fields.Selection([
        ('draft','Draft'),
        ('pending','Pending'),
        ('sold','Sold'),
        ('closed','Closed'),
    ], default='draft')

    # สร้าง contraint ไม่ให้ชื่อซ้ำกัน
    _sql_constraints = [
        ('unique_name', 'unique("name")', 'This name is exist!')
    ]

    line_ids = fields.One2many('property.line','property_id')
    active = fields.Boolean(default=True)

    @api.depends('create_time')
    def _compute_next_time(self):
        for rec in self:
            if rec.create_time:
                rec.next_time = rec.create_time + timedelta(hours=6)
            else:
                rec.next_time = False


    # depends จะเป็นให้มันขึ้นอยู่กับอะไร เมิ่อขึ้นอยู่กับอะไรแล้ว field นี้จะเป็นแบบเรียลไทม์เมื่อค่า field นั้นเปลี่ยนก็จะ compute ทันที
    @api.depends('expected_price','selling_price','owner_id.phone')
    # สร้าง compute เพื่อบอกว่า column นั้นจะทำอะไร
    def _compute_diff(self):
        for rec in self:
            print(rec)
            print("inside _compute_diff method")
            rec.diff = rec.expected_price - rec.selling_price
    
    @api.onchange('expected_price', 'owner_id.phone')
    def _onchange_expected_price(self):
        for rec in self:
            print(rec)
            print("inside onchange expected_price medthod")
            # ทำหน้า modal นั้นการแจ้งเตือน
            return {
                'warning': {'title': 'warning', 'message': 'negative value.', 'type': 'notification'}
            }

    # ดึงค่าจาก bedrooms มา เช็ค validate
    @api.constrains('bedrooms')
    def _check_bedrooms_greater_zero(self):
        for rec in self:
            if rec.bedrooms == 0:
                raise ValidationError('Please add valid number of bedrooms!')
    
    # สร้าง method
    def action_draft(self):
        for rec in self:
            rec.create_history_record(rec.state, 'draft')
            rec.state = 'draft'

    # สร้าง method
    def action_sold(self):
        for rec in self:
            rec.create_history_record(rec.state, 'sold')
            rec.state = 'sold'
            rec.write({
                'state' : 'sold'
            })

    def action_pending(self):
        for rec in self:
            rec.create_history_record(rec.state, 'pending')
            rec.state = 'pending'
            rec.write({
                'state' : 'pending'
            })

    def action_closed(self):
        for rec in self:
            rec.create_history_record(rec.state, 'closed')
            rec.state = 'closed'

    # สร้าง method ไว้เป็น scripts  ไว้สามารถตั้งให้มัน exec ตอนไหนก็ได้ตามที่เราสั่ง หรือเรียกว่า cron (automated actions)
    def check_expected_selling_date(self):
        property_ids = self.search([])
        for rec in property_ids:
            # check ว่ามี date ไหม ถ้ามีให้เช็คว่ามันเกินวันหมดอายุไหม
            if rec.expected_selling_date and rec.expected_selling_date < fields.date.today():
                rec.is_late = True
            else:
                rec.is_late = False

    def action(self):
        # สามารถหา name, id, login ได้ เช่น self.env.user.login คือ เข้ามาโดย สถานะ admin
        print(self.env.user.name)
        print(self.env.uid)
        print(self.env.company)
        print(self.env.context)
        
        # เช็ค sql db cursor
        print(self.env.cr)

        #สร้าง owner มาใหม่
        print(self.env['owner'].create({
            'name': 'name one',
            'phone' : '0100004934344'
        }))

        # ดู owner ว่ามีกี่ตัว สามารถใส่ เครื่องหมายได้นำหน้า และ default มันคือ หรือ (! & |)
        print(self.env['property'].search(['&', ('name', '!=', 'Property1'),('postcode', '=', '12345')]))

    # ทำ sequence ว่า อยากให้ชื่อ เป็น pattern เดียวกัน เช่น PRT00001
    @api.model
    def create(self, vals):
        res = super(Property, self).create(vals)
        if res.ref == 'New':
            res.ref = self.env['ir.sequence'].next_by_code('Property_seq')
        return res
    
    

    def create_history_record(self, old_state, new_state, reason=""):
        for rec in self:
            rec.env['property.history'].create({
                'user_id': rec.env.uid,
                'property_id': rec.id,
                'old_state': old_state,
                'new_state' : new_state,
                'reason': reason or "",
                'line_ids': [(0,0,{'description': line.description, 'area': line.area})for line in rec.line_ids],
            })

    def action_open_change_state_wizard(self):
        action = self.env['ir.actions.actions']._for_xml_id('practice.change_state_wizard_action')
        action['context'] = {'default_property_id' : self.id}
        return action
    
    # กดแล้วจะเปิดหน้าแสดงข้อมูล form owner ขึ้นมา
    def action_open_related_owner(self):
        action = self.env['ir.actions.actions']._for_xml_id('practice.owner_action')
        view_id = self.env.ref('practice.owner_view_form').id
        action['res_id'] = self.owner_id.id
        action['views'] = [[view_id, 'form']]
        return action
    
    
    # เมื่อสร้าง record จะแสดงปริ้น
    # @api.model_create_multi
    # def create(self, vals):
    #     res = super(Property, self).create(vals)
    #     print("inside create method")
    #     return res
    
    # เมื่อเข้าหน้านั้น record จะแสดงปริ้น
    # @api.model
    # def _search(self,domain, offset=0, limit=None, order=None, access_rights_uid=None):
    #     res = super(Property, self)._search(domain, offset=0, limit=None, order=None, access_rights_uid=None)
    #     print("inside search method")
    #     return res
    
    # เมื่อทำการแก้ไข record จะแสดงปริ้น
    # def write(self, vals):
    #     res = super(Property, self).write(vals)
    #     print("inside write method")
    #     return res
    
    # เมื่อลบ record จะแสดงปริ้น
    # def unlink(self):
    #     res = super(Property, self).unlink()
    #     print("inside unlink method")
    #     return res


class PropertyLine(models.Model):
    _name = 'property.line'

    property_id = fields.Many2one('property')
    area = fields.Float()
    description = fields.Char()
