import json
from decimal import Decimal

from app.constants.jobs import JOB_GENERATE_MONTHLY_PAYROLL
from app.jobs.base_batch_job import BaseBatchJob
from app.models.batch_models import JobStats
from app.models.payroll_item_model import PayrollItem
from app.models.payroll_model import PayrollAmounts
from app.services.email_service import EmailService
from app.services.payroll_calculation_service import PayrollCalculationService
from app.services.payroll_data_service import PayrollDataService


class GenerateMonthlyPayrollJob(BaseBatchJob):
    JOB_NAME = JOB_GENERATE_MONTHLY_PAYROLL

    def __init__(self, connection, email_service: EmailService, lock_owner: str = "batch-container"):
        super().__init__(connection=connection, job_name=self.JOB_NAME, lock_owner=lock_owner)
        self.email_service = email_service
        self.data_service = PayrollDataService(connection)
        self.calc_service = PayrollCalculationService()

    def process(self, execution_id: int) -> JobStats:
        stats = JobStats()
        failures: list[dict] = []
        context = self.data_service.resolve_payroll_context()
        users = self.data_service.get_active_payroll_users()

        self.logger.info("Generating payroll for month=%s year=%s users=%s", context.month, context.year, len(users))

        for user in users:
            user_id = user.id
            try:
                salary_config = self.data_service.get_active_salary_config(user_id, context.start_date, context.end_date)
                if salary_config is None:
                    stats.skipped += 1
                    self.mark_item_skipped(execution_id, "payroll_user", user_id, "No active salary config.")
                    self.connection.commit()
                    continue

                existing = self.data_service.get_existing_payroll(user_id, context.month, context.year)
                if existing:
                    if existing.status != 1:
                        stats.skipped += 1
                        self.mark_item_skipped(
                            execution_id,
                            "payroll_user",
                            user_id,
                            f"Payroll already exists with non-draft status={existing.status}.",
                        )
                        self.connection.commit()
                        continue
                    payroll_id = existing.id
                    self.data_service.reset_draft_payroll(payroll_id, salary_config.id)
                else:
                    payroll_id = self.data_service.create_payroll_draft(user_id, salary_config.id, context.month, context.year)

                base_amount = salary_config.base_salary
                self.data_service.insert_payroll_item(self.calc_service.build_base_item(payroll_id, base_amount))

                teaching_amount = Decimal("0")
                if salary_config.salary_type in (2, 4):
                    teaching_count = self.data_service.count_completed_sessions(user_id, context.start_date, context.end_date)
                    teaching_amount, teaching_item = self.calc_service.calculate_teaching_amount(salary_config, teaching_count)
                    if teaching_item is not None:
                        self.data_service.insert_payroll_item(self._with_payroll_id(teaching_item, payroll_id))

                kpi_amount = Decimal("0")
                if salary_config.salary_type in (3, 4):
                    staff_id = self.data_service.get_staff_id_by_user_id(user_id)
                    if staff_id is not None:
                        kpi = self.data_service.get_sales_kpi_totals(staff_id, context.month, context.year)
                        kpi_amount, kpi_item = self.calc_service.calculate_kpi_amount(salary_config, kpi)
                        if kpi_item is not None:
                            self.data_service.insert_payroll_item(self._with_payroll_id(kpi_item, payroll_id))

                amounts = self.calc_service.calculate_payroll_amounts(
                    base_amount=base_amount,
                    teaching_amount=teaching_amount,
                    kpi_amount=kpi_amount,
                )
                self.data_service.update_payroll_amounts(payroll_id, amounts)

                self.mark_item_success(execution_id, "payroll", payroll_id)
                self.connection.commit()
                stats.created += 1
                self._send_payroll_email(user_id, context.month, context.year, amounts)
            except Exception as ex:
                self.connection.rollback()
                self.mark_item_failed(execution_id, "payroll_user", user_id, str(ex))
                self.connection.commit()
                stats.failed += 1
                failures.append({"user_id": user_id, "reason": str(ex)})
                self.logger.exception("Failed generate payroll for user_id=%s", user_id)

        self.logger.info(
            json.dumps(
                {
                    "month": context.month,
                    "year": context.year,
                    "summary": {"created": stats.created, "skipped": stats.skipped, "failed": stats.failed},
                    "failure_details": failures,
                },
                ensure_ascii=False,
            )
        )
        return stats

    @staticmethod
    def _with_payroll_id(item: PayrollItem, payroll_id: int) -> PayrollItem:
        return PayrollItem(
            payroll_id=payroll_id,
            item_type=item.item_type,
            quantity=item.quantity,
            unit_amount=item.unit_amount,
            amount=item.amount,
            description=item.description,
        )

    def _send_payroll_email(self, user_id: int, month: int, year: int, amounts: PayrollAmounts):
        contact = self.data_service.get_user_contact(user_id)
        if contact is None or not contact.email:
            self.logger.warning("Skip payroll email user_id=%s: missing contact email", user_id)
            return

        full_name = contact.full_name or "User"
        try:
            self.email_service.send_payroll_generated(
                to_email=contact.email,
                full_name=full_name,
                month=month,
                year=year,
                base_amount=str(amounts.base_amount),
                teaching_amount=str(amounts.teaching_amount),
                kpi_amount=str(amounts.kpi_amount),
                gross_amount=str(amounts.gross_amount),
                net_amount=str(amounts.net_amount),
            )
            self.logger.info("Payroll email sent user_id=%s email=%s", user_id, contact.email)
        except Exception as ex:
            self.logger.warning("Payroll email failed user_id=%s email=%s reason=%s", user_id, contact.email, ex)
