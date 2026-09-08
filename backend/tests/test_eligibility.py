"""Tests for the pre-evaluation eligibility filter."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock

from pookie_backend.eligibility import check_eligibility


def _job(
    *,
    title: str = "Software Engineer",
    location: str = "New York, NY",
    salary_unknown: bool = True,
    salary_min: Decimal | None = None,
    salary_max: Decimal | None = None,
) -> MagicMock:
    job = MagicMock()
    job.canonical_title = title
    job.canonical_location = location
    job.salary_unknown = salary_unknown
    job.salary_min = salary_min
    job.salary_max = salary_max
    return job


_UNSET = object()


def _profile(
    *,
    allowed_locations: list[str] | None | object = _UNSET,
    salary_floor: Decimal | None | object = _UNSET,
) -> MagicMock:
    profile = MagicMock()
    profile.allowed_locations = (
        ["New York, NY"] if allowed_locations is _UNSET else allowed_locations
    )
    profile.salary_floor = (
        Decimal("170000.00") if salary_floor is _UNSET else salary_floor
    )
    return profile


# --- Engineering role filter ---


class TestEngineeringRoleFilter:
    def test_passes_software_engineer(self):
        assert check_eligibility(_job(title="Software Engineer"), _profile()) is None

    def test_passes_backend_developer(self):
        assert check_eligibility(_job(title="Backend Developer"), _profile()) is None

    def test_passes_sde_title(self):
        assert check_eligibility(_job(title="SDE II"), _profile()) is None

    def test_passes_swe_title(self):
        assert check_eligibility(_job(title="SWE - Platform"), _profile()) is None

    def test_passes_fullstack_engineer(self):
        assert check_eligibility(_job(title="Full Stack Engineer"), _profile()) is None

    def test_rejects_devops_engineer(self):
        assert check_eligibility(_job(title="DevOps Engineer"), _profile()) == "not_engineering_role"

    def test_rejects_devops_developer(self):
        assert check_eligibility(_job(title="DevOps Developer"), _profile()) == "not_engineering_role"

    def test_rejects_software_devops_engineer(self):
        assert check_eligibility(_job(title="Software DevOps Engineer"), _profile()) == "non_engineering_specialty"

    def test_rejects_sre(self):
        assert check_eligibility(_job(title="Site Reliability Engineer"), _profile()) == "not_engineering_role"

    def test_rejects_sre_abbreviation(self):
        assert check_eligibility(_job(title="SRE - Platform"), _profile()) == "not_engineering_role"

    def test_rejects_software_sre(self):
        assert check_eligibility(_job(title="Software Engineer, SRE"), _profile()) == "non_engineering_specialty"

    def test_passes_software_development_engineer(self):
        assert check_eligibility(_job(title="Software Development Engineer"), _profile()) is None

    def test_rejects_platform_engineer(self):
        assert check_eligibility(_job(title="Platform Engineer"), _profile()) == "not_engineering_role"

    def test_rejects_infrastructure_engineer(self):
        assert check_eligibility(_job(title="Infrastructure Engineer"), _profile()) == "not_engineering_role"

    def test_passes_frontend_engineer(self):
        assert check_eligibility(_job(title="Frontend Engineer"), _profile()) is None

    def test_rejects_product_manager(self):
        assert check_eligibility(_job(title="Product Manager"), _profile()) == "not_engineering_role"

    def test_rejects_designer(self):
        assert check_eligibility(_job(title="UX Designer"), _profile()) == "not_engineering_role"

    def test_rejects_data_analyst(self):
        assert check_eligibility(_job(title="Data Analyst"), _profile()) == "not_engineering_role"

    def test_rejects_recruiter(self):
        assert check_eligibility(_job(title="Technical Recruiter"), _profile()) == "not_engineering_role"

    def test_rejects_marketing(self):
        assert check_eligibility(_job(title="Marketing Manager"), _profile()) == "not_engineering_role"

    def test_rejects_sales_engineer(self):
        assert check_eligibility(_job(title="Sales Engineer"), _profile()) == "not_engineering_role"

    def test_rejects_solutions_engineer(self):
        assert check_eligibility(_job(title="Solutions Engineer"), _profile()) == "not_engineering_role"

    def test_rejects_support_engineer(self):
        assert check_eligibility(_job(title="Support Engineer"), _profile()) == "not_engineering_role"

    def test_rejects_customer_engineer(self):
        assert check_eligibility(_job(title="Customer Engineer"), _profile()) == "not_engineering_role"

    def test_rejects_security_engineer(self):
        assert check_eligibility(_job(title="Security Engineer"), _profile()) == "not_engineering_role"

    def test_rejects_network_engineer(self):
        assert check_eligibility(_job(title="Network Engineer"), _profile()) == "not_engineering_role"

    def test_rejects_hardware_engineer(self):
        assert check_eligibility(_job(title="Hardware Engineer"), _profile()) == "not_engineering_role"

    def test_rejects_design_engineer(self):
        assert check_eligibility(_job(title="Design Engineer"), _profile()) == "not_engineering_role"

    def test_rejects_business_systems_engineer(self):
        assert check_eligibility(_job(title="GTM Business Systems Engineer"), _profile()) == "not_engineering_role"

    def test_rejects_erp_developer(self):
        assert check_eligibility(_job(title="Oracle ERP Fusion Technical Developer"), _profile()) == "not_engineering_role"

    def test_rejects_recruiter_with_engineering(self):
        assert check_eligibility(_job(title="Technical Recruiter | Engineering"), _profile()) == "not_engineering_role"

    def test_rejects_tpm(self):
        assert check_eligibility(_job(title="TPM, Infrastructure"), _profile()) == "not_engineering_role"

    def test_rejects_software_sales_engineer(self):
        assert check_eligibility(_job(title="Software Sales Engineer"), _profile()) == "non_engineering_specialty"

    def test_rejects_data_engineer(self):
        assert check_eligibility(_job(title="Senior Data Engineer - Revenue Data Platform"), _profile()) == "not_engineering_role"

    def test_rejects_security_data_engineer(self):
        assert check_eligibility(_job(title="Senior Security Data Engineer"), _profile()) == "not_engineering_role"

    def test_rejects_pm_with_platform_suffix(self):
        assert check_eligibility(_job(title="Senior Product Manager - Observability Data Platform"), _profile()) == "not_engineering_role"

    def test_rejects_engineering_compensation_partner(self):
        assert check_eligibility(_job(title="Engineering Compensation Partner"), _profile()) == "not_engineering_role"

    def test_rejects_director_of_engineering(self):
        assert check_eligibility(_job(title="Director of Engineering"), _profile()) == "not_engineering_role"

    def test_rejects_vp_of_engineering(self):
        assert check_eligibility(_job(title="VP of Engineering"), _profile()) == "not_engineering_role"

    def test_rejects_head_of_engineering(self):
        assert check_eligibility(_job(title="Head of Engineering"), _profile()) == "not_engineering_role"

    def test_rejects_engineering_manager(self):
        assert check_eligibility(_job(title="Engineering Manager, Revenue"), _profile()) == "not_engineering_role"

    def test_rejects_manager_engineering(self):
        assert check_eligibility(_job(title="Manager, Engineering Platform"), _profile()) == "not_engineering_role"

    def test_passes_software_engineer_security(self):
        assert check_eligibility(_job(title="Software Engineer, Security"), _profile()) is None


# --- Seniority filter ---


class TestSeniorityFilter:
    def test_passes_junior(self):
        assert check_eligibility(_job(title="Junior Software Engineer"), _profile()) is None

    def test_passes_mid_level(self):
        assert check_eligibility(_job(title="Software Engineer"), _profile()) is None

    def test_rejects_senior(self):
        assert check_eligibility(_job(title="Senior Software Engineer"), _profile()) == "seniority_too_high"

    def test_rejects_senior_mid_title(self):
        assert check_eligibility(_job(title="Software Engineer (Senior)"), _profile()) == "seniority_too_high"

    def test_rejects_staff(self):
        assert check_eligibility(_job(title="Staff Software Engineer"), _profile()) == "seniority_too_high"

    def test_rejects_principal(self):
        assert check_eligibility(_job(title="Principal Software Engineer"), _profile()) == "seniority_too_high"

    def test_rejects_distinguished(self):
        assert check_eligibility(_job(title="Distinguished Software Engineer"), _profile()) == "seniority_too_high"


# --- Location filter ---


class TestLocationFilter:
    def test_passes_new_york(self):
        assert check_eligibility(_job(location="New York, NY"), _profile()) is None

    def test_passes_nyc(self):
        assert check_eligibility(_job(location="NYC"), _profile()) is None

    def test_passes_manhattan(self):
        assert check_eligibility(_job(location="Manhattan, New York"), _profile()) is None

    def test_passes_brooklyn(self):
        assert check_eligibility(_job(location="Brooklyn, NY"), _profile()) is None

    def test_passes_remote(self):
        assert check_eligibility(_job(location="Remote"), _profile()) is None

    def test_passes_remote_us(self):
        assert check_eligibility(_job(location="Remote (US)"), _profile()) is None

    def test_passes_united_states(self):
        assert check_eligibility(_job(location="United States"), _profile()) is None

    def test_passes_usa(self):
        assert check_eligibility(_job(location="USA"), _profile()) is None

    def test_passes_anywhere(self):
        assert check_eligibility(_job(location="Anywhere"), _profile()) is None

    def test_rejects_san_francisco(self):
        assert check_eligibility(_job(location="San Francisco, CA"), _profile()) == "location_mismatch"

    def test_rejects_seattle(self):
        assert check_eligibility(_job(location="Seattle, WA"), _profile()) == "location_mismatch"

    def test_rejects_london(self):
        assert check_eligibility(_job(location="London, UK"), _profile()) == "location_mismatch"


# --- Salary filter ---


class TestSalaryFilter:
    def test_passes_when_salary_unknown(self):
        assert check_eligibility(_job(salary_unknown=True), _profile()) is None

    def test_passes_when_salary_above_floor(self):
        job = _job(salary_unknown=False, salary_min=Decimal("180000"), salary_max=Decimal("220000"))
        assert check_eligibility(job, _profile()) is None

    def test_passes_when_salary_equals_floor(self):
        job = _job(salary_unknown=False, salary_min=Decimal("170000"), salary_max=Decimal("170000"))
        assert check_eligibility(job, _profile()) is None

    def test_rejects_when_salary_below_floor(self):
        job = _job(salary_unknown=False, salary_min=Decimal("120000"), salary_max=Decimal("150000"))
        assert check_eligibility(job, _profile()) == "salary_below_floor"

    def test_uses_max_salary_for_comparison(self):
        job = _job(salary_unknown=False, salary_min=Decimal("150000"), salary_max=Decimal("200000"))
        assert check_eligibility(job, _profile()) is None

    def test_passes_when_no_salary_floor_on_profile(self):
        job = _job(salary_unknown=False, salary_min=Decimal("50000"))
        assert check_eligibility(job, _profile(salary_floor=None)) is None


# --- Combined filter priority ---


class TestFilterPriority:
    def test_role_checked_before_location(self):
        job = _job(title="Product Manager", location="San Francisco, CA")
        assert check_eligibility(job, _profile()) == "not_engineering_role"

    def test_seniority_checked_before_location(self):
        job = _job(title="Staff Software Engineer", location="San Francisco, CA")
        assert check_eligibility(job, _profile()) == "seniority_too_high"

    def test_all_criteria_pass(self):
        job = _job(
            title="Backend Engineer",
            location="New York, NY",
            salary_unknown=False,
            salary_min=Decimal("180000"),
            salary_max=Decimal("220000"),
        )
        assert check_eligibility(job, _profile()) is None
