# Copyright 2017-19 ForgeFlow S.L. (https://www.forgeflow.com)
# Copyright 2024 Moduon Team (https://www.moduon.team)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import json
from ast import literal_eval

from lxml import etree

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.osv.expression import OR
from odoo.tools.misc import frozendict

BASE_EXCEPTION_FIELDS = ["message_follower_ids", "access_token"]


class TierValidation(models.AbstractModel):
    _name = "tier.validation"
    _description = "Tier Validation (abstract)"

    _tier_validation_buttons_xpath = "/form/header/button[last()]"
    _tier_validation_manual_config = True

    _state_field = "state"
    _state_from = ["draft"]
    _state_to = ["confirmed"]
    _cancel_state = "cancel"

    # TODO: step by step validation?
    review_ids = fields.One2many(
        comodel_name="tier.review",
        inverse_name="res_id",
        string="Validations",
        domain=lambda self: [("model", "=", self._name)],
        auto_join=True,
    )
    to_validate_message = fields.Html(compute="_compute_validated_rejected")
    # TODO: Delete in v17 in favor of validation_status field
    validated = fields.Boolean(
        compute="_compute_validated_rejected", search="_search_validated"
    )
    validated_message = fields.Html(compute="_compute_validated_rejected")

    need_validation = fields.Boolean(compute="_compute_need_validation")
    # TODO: Delete in v17 in favor of validation_status field
    rejected = fields.Boolean(
        compute="_compute_validated_rejected", search="_search_rejected"
    )
    rejected_message = fields.Html(compute="_compute_validated_rejected")
    # Informative field (used in purchase_tier_validation), will be reliable as of v17
    validation_status = fields.Selection(
        selection=[
            ("no", "Without validation"),
            ("pending", "Pending"),
            ("rejected", "Rejected"),
            ("validated", "Validated"),
        ],
        default="no",
        compute="_compute_validation_status",
    )
    reviewer_ids = fields.Many2many(
        string="Reviewers",
        comodel_name="res.users",
        compute="_compute_reviewer_ids",
        search="_search_reviewer_ids",
    )
    can_review = fields.Boolean(
        compute="_compute_can_review", search="_search_can_review"
    )
    has_comment = fields.Boolean(compute="_compute_has_comment")
    next_review = fields.Char(compute="_compute_next_review")

    def _compute_has_comment(self):
        for rec in self:
            has_comment = rec.review_ids.filtered(
                lambda r: r.status == "pending" and (self.env.user in r.reviewer_ids)
            ).mapped("has_comment") # ฟิลเตอร์หา สเตตัส pending และ หาผู้ใช้ ที่ตรงกับใน revierwer_ids ดึงแค่ has_comment ออกมา
            rec.has_comment = True in has_comment # ไปลูปหา True ดูอีกทีว่ามีไหม

    def _get_sequences_to_approve(self, user):
        # หาผู้ใช้ที่ในสถานะ pending
        all_reviews = self.review_ids.filtered(lambda r: r.status == "pending")
        
        #ลูปหา user ใน reviewer_ids
        my_reviews = all_reviews.filtered(lambda r: user in r.reviewer_ids)
        # Include all my_reviews with approve_sequence = False 
        # ดึง seq ที่ยังไม่ได้ approve มาทั้งหมด
        sequences = my_reviews.filtered(lambda r: not r.approve_sequence).mapped(
            "sequence"
        )
        # สมมุติว่า my  review เป็นแบบนี้
#         my_reviews = [
#     {
#         "sequence": 1,
#         "approve_sequence": True,
#         "status": "approved",
#     },
#     {
#         "sequence": 2,
#         "approve_sequence": False,
#         "status": "pending",
#     },
#     {
#         "sequence": 3,
#         "approve_sequence": True,
#         "status": "approved",
#     },
# ]
        # Include only my_reviews with approve_sequence = True
        approve_sequences = my_reviews.filtered("approve_sequence").mapped("sequence")
        # ถ้าผ่านคำสั่งข้างบนจะเหลือคำตอบเป็น [1, 3]

        #sorted
        if approve_sequences:
            my_sequence = min(approve_sequences)
            min_sequence = min(all_reviews.mapped("sequence"))
            if my_sequence <= min_sequence:
                sequences.append(my_sequence)
        return sequences

    def _compute_can_review(self):
        for rec in self:
            # จะได้ seq ที่เรียงไว้แล้วมาดูว่าใคร review ได้
            rec.can_review = rec._get_sequences_to_approve(self.env.user)

    @api.model
    def _search_can_review(self, operator, value):
        domain = [
            ("review_ids.reviewer_ids", "=", self.env.user.id),
            ("review_ids.status", "=", "pending"),
            ("review_ids.can_review", "=", True),
            ("rejected", "=", False),
        ]
        if "active" in self._fields:
            domain.append(("active", "in", [True, False]))
        # search ให้ตรงเงื่อนไข
        res_ids = self.search(domain).filtered("can_review").ids
        return [("id", "in", res_ids)]

    @api.depends("review_ids")
    def _compute_reviewer_ids(self):
        for rec in self:
            # หาสถานะ pending
            rec.reviewer_ids = rec.review_ids.filtered(
                lambda r: r.status == "pending"
            ).mapped("reviewer_ids")

    @api.model
    def _search_validated(self, operator, value):
        # ทำพวก statement
        assert operator in ("=", "!="), "Invalid domain operator"
        assert value in (True, False), "Invalid domain value"

        pos = self.search(
            # _state_field = state _state_from= draft
            #
            [(self._state_field, "in", self._state_from), ("review_ids", "!=", False)]
        ).filtered(lambda r: r.validated == value)
        return [("id", "in", pos.ids)]

    @api.model
    def _search_rejected(self, operator, value):
        # ถ้า ไม่ใช่ = , != 
        assert operator in ("=", "!="), "Invalid domain operator"
        # ถ้า ไม่ใช่ True, False
        assert value in (True, False), "Invalid domain value"

        pos = self.search(
            # review_ids ต้องมี
            [(self._state_field, "in", self._state_from), ("review_ids", "!=", False)]
        ).filtered(lambda r: r.rejected == value)
        return [("id", "in", pos.ids)]

    @api.model
    def _search_reviewer_ids(self, operator, value):

        model_operator = "in"
        if operator == "=" and value in ("[]", False):
            # Search for records that have not yet been through a validation
            # process.
            operator = "!="
            model_operator = "not in"
        reviews = self.env["tier.review"].search(
            [
                ("model", "=", self._name),
                ("reviewer_ids", operator, value),
                ("can_review", "=", True),
                ("status", "=", "pending"),
            ]
        )
        return [("id", model_operator, list(set(reviews.mapped("res_id"))))]

    def _get_to_validate_message_name(self):
        # getter description
        return self._description

    def _get_to_validate_message(self):
        # เอาไปใช้ข้างล่างที่ record ที่เป็น html
        return (
            """<i class="fa fa-info-circle" /> %s"""
            % _("This %s needs to be validated")
            % self._get_to_validate_message_name()
        )

    def _get_validated_message(self):
        msg = """<i class="fa fa-thumbs-up" /> %s""" % _(
            """Operation has been <b>validated</b>!"""
        )
        return self.validated and msg or ""

    def _get_rejected_message(self):
        msg = """<i class="fa fa-thumbs-down" /> %s""" % _(
            """Operation has been <b>rejected</b>."""
        )
        return self.rejected and msg or ""

    def _compute_validated_rejected(self):
        for rec in self:
            # เอาไปเช็คใน _calc_reviews_validated ถ้า approved หมดจะ return true
            rec.validated = self._calc_reviews_validated(rec.review_ids)
            
            # เอาแมสเซส
            rec.validated_message = rec._get_validated_message()

            # เอาไปเช็คใน _calc_reviews_validated ถ้ามี rejected สักหนึ่งรายการ จะ return true
            rec.rejected = self._calc_reviews_rejected(rec.review_ids)

            # เอาแมสเซส
            rec.rejected_message = rec._get_rejected_message()
            # เอาแมสเซส
            rec.to_validate_message = rec._get_to_validate_message()

    def _compute_validation_status(self):
        for item in self:
            # ไม่ใช่ rejected ให้ status เป็น validated
            if item.validated and not item.rejected:
                item.validation_status = "validated"
            # ใช่ rejected ให้ status เป็น rejected
            elif not item.validated and item.rejected:
                item.validation_status = "rejected"
            elif (
                # ไม่ใช่ validated
                not item.validated
                # ไม่ใช่ tejected
                and not item.rejected
                # และยังมี review_ids ที่เป็น status pending อยู่
                and any(item.review_ids.filtered(lambda x: x.status == "pending"))
            ):
                # ให้ status เป็น pending
                item.validation_status = "pending"
            else:
                # status = no
                item.validation_status = "no"

    def _compute_next_review(self):
        for rec in self:
            # ดึง review_ids แล้ว sorted sequence และหาที่เป็น status = pending แล้วเอาแค่ตัวแรกตัวเดียว
            review = rec.review_ids.sorted("sequence").filtered(
                lambda l: l.status == "pending"
            )[:1]
            # next_review ต้องมี review และเป็น string พร้อมชื่อ review
            rec.next_review = review and _("Next: %s") % review.name or ""

    @api.model
    def _calc_reviews_validated(self, reviews):
        """Override for different validation policy."""
        
        if not reviews:
            return False
        #         reviews = [
        # {"status": "approved"},
        # {"status": "approved"},
        # {"status": "approved"},
        # จะ return true
# ]
        # ["approved", "approved", "pending"] จะแปลงเป็น [False, False, True] หมายความว่า approved ทั้งหมดถึงจะส่ง true ออกมา
        return not any([s != "approved" for s in reviews.mapped("status")])

    @api.model
    def _calc_reviews_rejected(self, reviews):
        """Override for different rejection policy."""
        # ถ้ามี rejected สักหนึ่งรายการ จะ return true
        return any([s == "rejected" for s in reviews.mapped("status")])


    # ดูว่าต้อง validation ไหม
    def _compute_need_validation(self):
        for rec in self:
            # print("rec.id ===>", rec.id)
            # print("models.NewId ===>", models.NewId)
            # print("ininstance ==>",isinstance(rec.id, models.NewId))
            # เช็คว่าเป็น type และค่าเหมือนกันไหม
            if isinstance(rec.id, models.NewId):
                
                # need validation เป็น false
                rec.need_validation = False
                continue

            # ส่วนที่ตั้งว่า ต้องการ validation แบบไหน
            tiers = self.env["tier.definition"].search(
                [
                    ("model", "=", self._name),
                    ("company_id", "in", [False] + self.env.company.ids),
                ]
            )
            # print("_name ==>", self._name)
            # print("self.env.company.ids ==>", self.env.company.ids)
            # print("[False] + self.env.company.ids ==>", [False] + self.env.company.ids)
            # print("tiers ==>", tiers)
            
            valid_tiers = any([rec.evaluate_tier(tier) for tier in tiers])
            # print("valid_tiers ==>", valid_tiers)
            # จะไม่มี review_ids และ มี valid_tiers และ _check_state_from_condition
            rec.need_validation = (
                not rec.review_ids and valid_tiers and rec._check_state_from_condition()
            )
            # print("not rec.review_ids ==>" ,not rec.review_ids)
            # print("rec.need_validation ==>", rec.need_validation)
            # print("rec.review_ids ==>", rec.review_ids)
            # print("rec._check_state_from_condition() ==> ", rec._check_state_from_condition())

    def evaluate_tier(self, tier):
        if tier.definition_domain:
            # literal คือ ข้อมูล เช่น ส่ง '123' มันจะแปลงเป็น int ให้
            domain = literal_eval(tier.definition_domain)
            return self.filtered_domain(domain)
        else:
            return self

    @api.model
    def _get_validation_exceptions(self, extra_domain=None, add_base_exceptions=True):
        """Return Tier Validation Exception field names that matchs custom domain."""
        # exception = ข้อยกเว้น 
        exception_fields = (
            self.env["tier.validation.exception"]
            .search(
                [
                    ("model_name", "=", self._name),
                    ("company_id", "in", [False] + self.env.company.ids),
                    *(extra_domain or []),
                ]
            )
            .mapped("field_ids.name")
        )
        # print("exception_fields  old ==>", exception_fields)
        if add_base_exceptions:
            exception_fields = list(set(exception_fields + BASE_EXCEPTION_FIELDS))
            # print("exception_fields new ==>", exception_fields)
        return exception_fields

    @api.model
    def _get_all_validation_exceptions(self):
        """Extend for more field exceptions to be written when on the entire
        validation process."""
        return self._get_validation_exceptions()

    @api.model
    def _get_under_validation_exceptions(self):
        # แบบนี้ extra_domain
        """Extend for more field exceptions to be written under validation."""
        return self._get_validation_exceptions(
            extra_domain=[("allowed_to_write_under_validation", "=", True)]
        )

    @api.model
    def _get_after_validation_exceptions(self):
        # แบบนี้ extra_domain
        """Extend for more field exceptions to be written after validation."""
        return self._get_validation_exceptions(
            extra_domain=[("allowed_to_write_after_validation", "=", True)]
        )

    def _check_allow_write_under_validation(self, vals):
        """Allow to add exceptions for fields that are allowed to be written
        even when the record is under validation."""
        exceptions = self._get_under_validation_exceptions()
        for val in vals:
            # ถ้าไม่มีข้อยกเว้น ให้ return False
            if val not in exceptions:
                return False
        return True

    def _check_allow_write_after_validation(self, vals):
        """Allow to add exceptions for fields that are allowed to be written
        even when the record is after validation."""
        exceptions = self._get_after_validation_exceptions()
        for val in vals:
            # ถ้าไม่มีข้อยกเว้น ให้ return False
            if val not in exceptions:
                return False
        return True

    def _get_fields_to_write_validation(self, vals, records_exception_function):
        """Not allowed fields to write when validation depending on the given function."""
        exceptions = records_exception_function()
        not_allowed_fields = []
        for val in vals:
            # ถ้าไม่มีข้อยกเว้น
            if val not in exceptions:
                # เพิ่ม val เข้าไป
                not_allowed_fields.append(val)
        if not not_allowed_fields:
            # ถ้าไม่มีอะไรใน not_allowed_fields 
            return []

        not_allowed_field_names, allowed_field_names = [], []
        
        # แปลงเป็น dict
        for fld_name, fld_data in self.fields_get(
            not_allowed_fields + exceptions
        ).items():
        # แยกที่ได้รับ อนุญาติ และ ไม่อนุญาติ
            if fld_name in not_allowed_fields:
                not_allowed_field_names.append(fld_data["string"])
            else:
                allowed_field_names.append(fld_data["string"])
        return allowed_field_names, not_allowed_field_names

    def write(self, vals):
        print("create ========")
        # สร้าง validation
        for rec in self:
            # check condition 
            if rec._check_state_conditions(vals):
                print("condition pass =====")
                print("rec._check_state_conditions(vals) ==>", rec._check_state_conditions(vals))
                # ดูว่า ต้อง validation ไหม
                if rec.need_validation:
                    print("validation pass =====")
                    print("rec.need_validation ==>", rec.need_validation)
                    # try to validate operation
                    reviews = rec.request_validation()
                    print("pass request_validation ==")
                    print("reviews ==>", reviews)
                    rec._validate_tier(reviews)
                    # ถ้าไม่ได้ approved จะ error
                    if not self._calc_reviews_validated(reviews):
                        raise ValidationError(
                            _(
                                "This action needs to be validated for at least "
                                "one record. \nPlease request a validation."
                            )
                        )
                # ถ้ามี review_ids แต่ไม่มีการ validated
                if rec.review_ids and not rec.validated:
                    raise ValidationError(
                        _(
                            "A validation process is still open for at least "
                            "one record."
                        )
                    )
            # Write under validation
            if (
                # มี review_ids ไหม และ rec มี state(_state_field) ไหม ที่ชื่อตรงกับใน _state_from(draft)
                rec.review_ids
                and getattr(rec, self._state_field) in self._state_from
                # และตัว vals.get ต้องไม่มีค่า ใน _state_t(confirmed) และ _cancel_state(cancel)
                and not vals.get(self._state_field)
                in (self._state_to + [self._cancel_state])
                # เช็ค _check_allow_write_under_validation
                and not rec._check_allow_write_under_validation(vals)
                # check context ไม่มีคำว่า skip_validation_check
                and not rec._context.get("skip_validation_check")
            ):
                (
                    allowed_fields,
                    not_allowed_fields,
                ) = rec._get_fields_to_write_validation(
                    vals, rec._get_under_validation_exceptions
                )
                raise ValidationError(
                    _(
                        "You are not allowed to write those fields under validation.\n"
                        "- %(not_allowed_fields)s\n\n"
                        "Only those fields can be modified:\n- %(allowed_fields)s"
                    )
                    % {
                        "not_allowed_fields": "\n- ".join(not_allowed_fields),
                        "allowed_fields": "\n- ".join(allowed_fields),
                    }
                )

            # Write after validation. Check only if Tier Validation Exception is created
            if (
                rec._get_validation_exceptions(add_base_exceptions=False)
                and rec.validation_status == "validated"
                and getattr(rec, self._state_field)
                in (self._state_to + [self._cancel_state])
                and not rec._check_allow_write_after_validation(vals)
                and not rec._context.get("skip_validation_check")
            ):
                (
                    allowed_fields,
                    not_allowed_fields,
                ) = rec._get_fields_to_write_validation(
                    vals, rec._get_after_validation_exceptions
                )
                raise ValidationError(
                    _(
                        "You are not allowed to write those fields after validation.\n"
                        "- %(not_allowed_fields)s\n\n"
                        "Only those fields can be modified:\n- %(allowed_fields)s"
                    )
                    % {
                        "not_allowed_fields": "\n- ".join(not_allowed_fields),
                        "allowed_fields": "\n- ".join(allowed_fields),
                    }
                )
            if rec._allow_to_remove_reviews(vals):
                rec.mapped("review_ids").unlink()
        return super(TierValidation, self).write(vals)

    def _allow_to_remove_reviews(self, values):
        """Method for deciding whether the elimination of revisions is necessary."""
        self.ensure_one()
        state_to = values.get(self._state_field)
        if not state_to:
            return False
        state_from = self[self._state_field]
        # If you change to _cancel_state
        if state_to in (self._cancel_state):
            return True
        # If it is changed to _state_from and it was not in _state_from
        if state_to in self._state_from and state_from not in self._state_from:
            return True
        return False

    def _check_state_from_condition(self):
        # เช็ค context
        # print("self.env.context.get('skip_check_state_condition') ==>", self.env.context.get("skip_check_state_condition"))
        # print("_state_field ==>", self._state_field)
        # print("self._fields", self._fields)
        # print("getattr(self, self._state_field) ==>", getattr(self, self._state_field))
        # print("_state_from ==>", self._state_from)
        # print("getattr(self, self._state_field) in self._state_from ==>", getattr(self, self._state_field) in self._state_from)
        return self.env.context.get("skip_check_state_condition") or (
            self._state_field in self._fields
            and getattr(self, self._state_field) in self._state_from
        )

    def _check_state_conditions(self, vals):
        # ไม่รู้คืออะไร
        self.ensure_one()
        return (
            self._check_state_from_condition()
            and vals.get(self._state_field) in self._state_to
        )

    def _validate_tier(self, tiers=False):
        self.ensure_one()
        tier_reviews = tiers or self.review_ids
        # user ที่สถานะ pending
        user_reviews = tier_reviews.filtered(
            lambda r: r.status == "pending" and (self.env.user in r.reviewer_ids)
        )
        user_reviews.write(
            {
                "status": "approved",
                "done_by": self.env.user.id,
                "reviewed_date": fields.Datetime.now(),
            }
        )
        reviews_to_notify = user_reviews.filtered(
            lambda r: r.definition_id.notify_on_accepted
        )
        if reviews_to_notify:
            subscribe = "message_subscribe"
            # ถ้ามี message_subscribe ใน self
            if hasattr(self, subscribe):
                # ให้เอาออกมา 
                getattr(self, subscribe)(
                    partner_ids=reviews_to_notify.mapped("reviewer_ids")
                    .mapped("partner_id")
                    .ids
                )
            for review in reviews_to_notify:

                rec = self.env[review.model].browse(review.res_id)
                rec._notify_accepted_reviews()

    def _get_requested_notification_subtype(self):
        return "base_tier_validation.mt_tier_validation_requested"

    def _get_accepted_notification_subtype(self):
        return "base_tier_validation.mt_tier_validation_accepted"

    def _get_rejected_notification_subtype(self):
        return "base_tier_validation.mt_tier_validation_rejected"

    def _get_restarted_notification_subtype(self):
        return "base_tier_validation.mt_tier_validation_restarted"

    def _notify_accepted_reviews(self):
        post = "message_post"
        # มี message_post ใน self ไหม
        if hasattr(self, post):
            # Notify state change
            getattr(self.sudo(), post)(
                subtype_xmlid=self._get_accepted_notification_subtype(),
                body=self._notify_accepted_reviews_body(),
            )

    def _notify_accepted_reviews_body(self):
        # อีเมล
        # ใน review_ids มี user ที่เรา login ไหม  และ มีcomment ไหม ถ้าใช่ return true
        has_comment = self.review_ids.filtered(
            lambda r: (self.env.user in r.reviewer_ids) and r.comment
        )
        if has_comment:
            comment = has_comment.mapped("comment")[0]
            return _("A review was accepted. (%s)") % comment
        return _("A review was accepted")

    def _add_comment(self, validate_reject, reviews):
        # สร้าง wizard comment
        wizard = self.env.ref("base_tier_validation.view_comment_wizard")
        return {
            "name": _("Comment"),
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "res_model": "comment.wizard",
            "views": [(wizard.id, "form")],
            "view_id": wizard.id,
            "target": "new",
            "context": {
                "default_res_id": self.id,
                "default_res_model": self._name,
                "default_review_ids": reviews.ids,
                "default_validate_reject": validate_reject,
            },
        }

    def validate_tier(self):
        self.ensure_one()
        # หา sequece(sort)
        sequences = self._get_sequences_to_approve(self.env.user)
        # หา คน review ตาม seq 
        reviews = self.review_ids.filtered(
            lambda l: l.sequence in sequences or l.approve_sequence_bypass
        )
        # ถ้ามี comment
        if self.has_comment:
            # หา review ที่เป็น pending และ user ตรงกับ reviewer_ids
            user_reviews = reviews.filtered(
                lambda r: r.status == "pending" and (self.env.user in r.reviewer_ids)
            )
            
            return self._add_comment("validate", user_reviews)
        self._validate_tier(reviews)
        self._update_counter({"review_deleted": True})

    def reject_tier(self):
        self.ensure_one()
        # หา seq 
        sequences = self._get_sequences_to_approve(self.env.user)
        reviews = self.review_ids.filtered(lambda l: l.sequence in sequences)
        # ถ้ามี comment ให้ เป็น reject
        if self.has_comment:
            return self._add_comment("reject", reviews)
        self._rejected_tier(reviews)
        self._update_counter({"review_deleted": True})

    def _notify_rejected_review_body(self):
        has_comment = self.review_ids.filtered(
            lambda r: (self.env.user in r.reviewer_ids) and r.comment
        )
        # ส่วนไหนไม่รู้
        if has_comment:
            comment = has_comment.mapped("comment")[0]
            return _("A review was rejected by %(user)s. (%(comment)s)") % {
                "user": self.env.user.name,
                "comment": comment,
            }
        return _("A review was rejected by %s.") % (self.env.user.name)

    def _notify_rejected_review(self):
        post = "message_post"
        # หา message_post 
        if hasattr(self, post):
            # Notify state change
            getattr(self.sudo(), post)(
                subtype_xmlid=self._get_rejected_notification_subtype(),
                body=self._notify_rejected_review_body(),
            )

    def _rejected_tier(self, tiers=False):
        self.ensure_one()
        tier_reviews = tiers or self.review_ids
        # หา pending 
        user_reviews = tier_reviews.filtered(
            lambda r: r.status == "pending" and (self.env.user in r.reviewer_ids)
        )
        user_reviews.write(
            {
                "status": "rejected",
                "done_by": self.env.user.id,
                "reviewed_date": fields.Datetime.now(),
            }
        )

        reviews_to_notify = user_reviews.filtered(
            lambda r: r.definition_id.notify_on_rejected
        )
        # ถ้ามี 
        if reviews_to_notify:
            subscribe = "message_subscribe"
            if hasattr(self, subscribe):
                getattr(self, subscribe)(
                    partner_ids=reviews_to_notify.mapped("reviewer_ids")
                    .mapped("partner_id")
                    .ids
                )
            for review in reviews_to_notify:
                rec = self.env[review.model].browse(review.res_id)
                rec._notify_rejected_review()

    def _notify_requested_review_body(self):
        # แจ้งเตือนเมล
        return _("A review has been requested by %s.") % (self.env.user.name)

    def _notify_review_requested(self, tier_reviews):
        # หน้าแจ้งเตือน
        subscribe = "message_subscribe"
        post = "message_post"
        if hasattr(self, post) and hasattr(self, subscribe):
            for rec in self.sudo():
                users_to_notify = tier_reviews.filtered(
                    lambda r: r.definition_id.notify_on_create and r.res_id == rec.id
                ).mapped("reviewer_ids")
                # Subscribe reviewers and notify
                if len(users_to_notify) > 0:
                    getattr(rec, subscribe)(
                        partner_ids=users_to_notify.mapped("partner_id").ids
                    )
                    getattr(rec, post)(
                        subtype_xmlid=self._get_requested_notification_subtype(),
                        body=rec._notify_requested_review_body(),
                    )

    def _prepare_tier_review_vals(self, definition, sequence):
        return {
            "model": self._name,
            "res_id": self.id,
            "definition_id": definition.id,
            "requested_by": self.env.uid,
            "sequence": sequence,
        }

    def request_validation(self):
        td_obj = self.env["tier.definition"]
        tr_obj = self.env["tier.review"]
        vals_list = []
        for rec in self:
            # เช็ค context อาจจะมี bypass และเช็คว่ามี validation ไหม
            if rec._check_state_from_condition() and rec.need_validation:
                tier_definitions = td_obj.search(
                    [
                        ("model", "=", self._name),
                        ("company_id", "in", [False] + self.env.company.ids),
                    ],
                    order="sequence desc",
                )
                # print("tier_definitions ==>", tier_definitions)
                sequence = 0
                # หาเงื่อนไข 
                for td in tier_definitions:
                    # print("td ==>", td)
                    # print("rec.evaluate_tier(td) ==>", rec.evaluate_tier(td))
                    if rec.evaluate_tier(td):
                        sequence += 1
                        vals_list.append(rec._prepare_tier_review_vals(td, sequence))
                        # print("rec._prepare_tier_review_vals(td, sequence) ==>", rec._prepare_tier_review_vals(td, sequence))
                self._update_counter({"review_created": True})
                # print("self._update_counter({'review_created': True})", self._update_counter({"review_created": True}))

        created_trs = tr_obj.create(vals_list)
        # print("tr_obj ==>", tr_obj)
        # print("vals_list ==>", vals_list)
        # print("created_trs ==>", created_trs)
        self._notify_review_requested(created_trs)
        # print("self._notify_review_requested(created_trs) ==>", self._notify_review_requested(created_trs))
        return created_trs

    def _notify_restarted_review_body(self):
        return _("The review has been reset by %s.") % (self.env.user.name)

    def _notify_restarted_review(self):
        post = "message_post"
        # เช็ค message_post
        if hasattr(self, post):
            getattr(self.sudo(), post)(
                subtype_xmlid=self._get_restarted_notification_subtype(),
                body=self._notify_restarted_review_body(),
            )

    def restart_validation(self):
        for rec in self:
            partners_to_notify_ids = False
            if getattr(rec, self._state_field) in self._state_from:
                to_update_counter = (
                    rec.mapped("review_ids").filtered(lambda a: a.status == "pending")
                    and True
                    or False
                )
                reviews_to_notify = rec.review_ids.filtered(
                    lambda r: r.definition_id.notify_on_restarted
                )
                if reviews_to_notify:
                    partners_to_notify_ids = (
                        reviews_to_notify.mapped("reviewer_ids")
                        .mapped("partner_id")
                        .ids
                    )
                rec.mapped("review_ids").unlink()
                if to_update_counter:
                    self._update_counter({"review_deleted": True})
            if partners_to_notify_ids:
                subscribe = "message_subscribe"
                reviews_to_notify = rec.review_ids.filtered(
                    lambda r: r.definition_id.notify_on_restarted
                )
                if hasattr(self, subscribe):
                    getattr(self, subscribe)(partner_ids=partners_to_notify_ids)
                rec._notify_restarted_review()

    @api.model
    def _update_counter(self, review_counter):
        self.review_ids._compute_can_review()
        notifications = []
        channel = "base.tier.validation/updated"
        notifications.append([self.env.user.partner_id, channel, review_counter])
        self.env["bus.bus"]._sendmany(notifications)

    def unlink(self):
        self.mapped("review_ids").unlink()
        return super().unlink()

    def _add_tier_validation_buttons(self, node, params):
        str_element = self.env["ir.qweb"]._render(
            "base_tier_validation.tier_validation_buttons", params
        )
        new_node = etree.fromstring(str_element)
        return new_node

    def _add_tier_validation_label(self, node, params):
        str_element = self.env["ir.qweb"]._render(
            "base_tier_validation.tier_validation_label", params
        )
        new_node = etree.fromstring(str_element)
        return new_node

    def _add_tier_validation_reviews(self, node, params):
        str_element = self.env["ir.qweb"]._render(
            "base_tier_validation.tier_validation_reviews", params
        )
        new_node = etree.fromstring(str_element)
        return new_node

    def _get_tier_validation_readonly_domain(self):
        return [("review_ids", "!=", [])]

    @api.model
    def get_view(self, view_id=None, view_type="form", **options):
        res = super().get_view(view_id=view_id, view_type=view_type, **options)

        View = self.env["ir.ui.view"]

        # Override context for postprocessing
        if view_id and res.get("base_model", self._name) != self._name:
            View = View.with_context(base_model_name=res["base_model"])
        if view_type == "form" and not self._tier_validation_manual_config:
            doc = etree.XML(res["arch"])
            params = {
                "state_field": self._state_field,
                "state_operator": "not in",
                "state_value": self._state_from,
            }
            all_models = res["models"].copy()
            for node in doc.xpath(self._tier_validation_buttons_xpath):
                # By default, after the last button of the header
                # _add_tier_validation_buttons process
                new_node = self._add_tier_validation_buttons(node, params)
                new_arch, new_models = View.postprocess_and_fields(new_node, self._name)
                new_node = etree.fromstring(new_arch)
                for new_element in new_node:
                    node.addnext(new_element)
            for node in doc.xpath("/form/sheet"):
                # _add_tier_validation_label process
                new_node = self._add_tier_validation_label(node, params)
                new_arch, new_models = View.postprocess_and_fields(new_node, self._name)
                new_node = etree.fromstring(new_arch)
                for new_element in new_node:
                    node.addprevious(new_element)
                # _add_tier_validation_reviews process
                new_node = self._add_tier_validation_reviews(node, params)
                new_arch, new_models = View.postprocess_and_fields(new_node, self._name)
                for model in new_models:
                    if model in all_models:
                        continue
                    if model not in res["models"]:
                        all_models[model] = new_models[model]
                    else:
                        all_models[model] = res["models"][model]
                new_node = etree.fromstring(new_arch)
                node.append(new_node)
            excepted_fields = self._get_all_validation_exceptions()
            for node in doc.xpath("//field[@name][not(ancestor::field)]"):
                if node.attrib.get("name") in excepted_fields:
                    continue
                modifiers = json.loads(
                    node.attrib.get("modifiers", '{"readonly": false}')
                )
                if modifiers.get("readonly") is not True:
                    modifiers["readonly"] = OR(
                        [
                            modifiers.get("readonly", []) or [],
                            self._get_tier_validation_readonly_domain(),
                        ]
                    )
                    node.attrib["modifiers"] = json.dumps(modifiers)
            res["arch"] = etree.tostring(doc)
            res["models"] = frozendict(all_models)
        return res
