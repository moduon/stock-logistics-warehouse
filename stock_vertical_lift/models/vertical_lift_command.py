# Copyright 2019 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import logging

from odoo import _, api, exceptions, fields, models

_logger = logging.getLogger(__name__)


class VerticalLiftCommand(models.Model):
    _name = "vertical.lift.command"
    _order = "shuttle_id, name desc"
    _description = "commands sent to the shuttle"

    def _default_name(self):
        return self.env["ir.sequence"].next_by_code("vertical.lift.command")

    name = fields.Char(
        "Name", default=lambda s: s._default_name(), required=True, index=True
    )
    command = fields.Char(required=True)
    answer = fields.Char()
    error = fields.Char()
    shuttle_id = fields.Many2one("vertical.lift.shuttle", required=True)

    def record_answer(self, answer):
        name = self._get_key(answer)
        record = self.search([("name", "=", name)], limit=1)
        if not record:
            _logger.error("unable to match answer to a command: %r", answer)
            raise exceptions.UserError(_("Unknown record %s") % name)
        record.answer = answer
        record.shuttle_id._hardware_response_callback(record)
        return record

    def _get_key(self, answer):
        key = answer.split("|")[1:2]
        if key:
            return key[0]
        else:
            return ""

    @api.model_create_multi
    def create(self, vals_list):
        for values in vals_list:
            if "name" not in values:
                name = self._get_key(values.get("command"))
                if name:
                    values["name"] = name
        return super().create(vals_list)

    @api.autovacuum
    def _autovacuum_commands(self):
        _logger.info("Vacuuming ``vertical.lift.command`` records")
        count = 0
        param = self.env["ir.config_parameter"].sudo()
        value = param.get_param("stock_vertical_lift.delete_command_after_days")
        if value:
            try:
                days = int(value)  # ``value`` is a str, try casting to int
            except ValueError:
                _logger.warning(
                    "Cannot convert ``stock_vertical_lift.delete_command_after_days``"
                    f"'s value to integer: '{value}'"
                )
            else:
                limit = fields.Datetime.add(fields.Datetime.now(), days=-days)
                commands = self.search([("create_date", "<", limit)])
                if commands:
                    count = len(commands)
                    commands.unlink()
        _logger.info(f"Vacuumed {count} ``vertical.lift.command`` record(s)")
