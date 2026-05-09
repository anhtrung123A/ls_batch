from app.constants.jobs import JOB_CREATE_LEADS_FROM_EXCEL, JOB_GENERATE_MONTHLY_PAYROLL
from app.jobs.create_leads_from_excel_job import CreateLeadsFromExcelJob
from app.jobs.create_student_users_job import CreateStudentUsersJob
from app.jobs.generate_monthly_payroll_job import GenerateMonthlyPayrollJob
from app.services.email_service import EmailService


def build_jobs(connection, settings):
    def create_student_users():
        job = CreateStudentUsersJob(connection)
        job.set_email_service(EmailService(settings))
        return job

    def create_leads_from_excel():
        return CreateLeadsFromExcelJob(connection, settings)

    def generate_monthly_payroll():
        return GenerateMonthlyPayrollJob(connection, EmailService(settings))

    return {
        CreateStudentUsersJob.JOB_NAME: create_student_users,
        JOB_CREATE_LEADS_FROM_EXCEL: create_leads_from_excel,
        JOB_GENERATE_MONTHLY_PAYROLL: generate_monthly_payroll,
    }
