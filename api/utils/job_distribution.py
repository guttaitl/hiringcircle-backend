# ==========================================================
# JOB DISTRIBUTION MODULE - US JOB PORTALS AUTOMATION
# Posts jobs to LinkedIn, Indeed, ZipRecruiter, Glassdoor,
# CareerBuilder, Monster, and SimplyHired
# ==========================================================

import os
import json
import logging
import requests
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from dotenv import load_dotenv

# Load environment variables
ROOT_ENV = Path(__file__).resolve().parent.parent / ".env.development"
if os.getenv("RAILWAY_ENVIRONMENT") is None:
    load_dotenv(ROOT_ENV)

logger = logging.getLogger("job_distribution")


# ==========================================================
# ENUMS & DATA CLASSES
# ==========================================================

class PortalStatus(Enum):
    PENDING = "pending"
    POSTED = "posted"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class PortalResult:
    portal: str
    status: PortalStatus
    post_url: Optional[str] = None
    error_message: Optional[str] = None
    posted_at: Optional[str] = None
    external_id: Optional[str] = None


@dataclass
class JobPostData:
    """Standardized job data structure for all portals"""
    job_id: str
    title: str
    company: str
    location: str
    description: str
    skills: List[str]
    employment_type: str
    experience: str
    salary: str
    work_authorization: str
    visa_transfer: str
    apply_url: str
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    company_logo: Optional[str] = None
    company_website: Optional[str] = None

    @classmethod
    def from_job_dict(cls, job: dict) -> "JobPostData":
        """Convert internal job dict to standardized format"""
        skills = job.get("skills", "")
        skills_list = [s.strip() for s in skills.split(",") if s.strip()] if skills else []
        
        return cls(
            job_id=job.get("jobid", ""),
            title=job.get("job_title", ""),
            company=job.get("user_company") or "HiringCircle",
            location=job.get("location", "Remote"),
            description=job.get("job_description", ""),
            skills=skills_list,
            employment_type=job.get("employment_type", "Contract"),
            experience=job.get("experience", ""),
            salary=job.get("salary", ""),
            work_authorization=job.get("work_authorization", "Any"),
            visa_transfer=job.get("visa_transfer", "No"),
            apply_url=f"https://www.hiringcircle.us/apply/{job.get('jobid', '')}",
            contact_email=job.get("user_email"),
            company_website="https://www.hiringcircle.us"
        )


# ==========================================================
# CONFIGURATION
# ==========================================================

def get_portal_config() -> Dict:
    """Get all job portal API configurations from environment"""
    return {
        "linkedin": {
            "enabled": os.getenv("LINKEDIN_ENABLED", "false").lower() == "true",
            "client_id": os.getenv("LINKEDIN_CLIENT_ID"),
            "client_secret": os.getenv("LINKEDIN_CLIENT_SECRET"),
            "access_token": os.getenv("LINKEDIN_ACCESS_TOKEN"),
            "organization_id": os.getenv("LINKEDIN_ORGANIZATION_ID"),
            "api_version": "202401"
        },
        "indeed": {
            "enabled": os.getenv("INDEED_ENABLED", "false").lower() == "true",
            "api_key": os.getenv("INDEED_API_KEY"),
            "secret": os.getenv("INDEED_SECRET"),
            "publisher_id": os.getenv("INDEED_PUBLISHER_ID"),
            "endpoint": "https://ads.indeed.com/api/v1/job postings"
        },
        "ziprecruiter": {
            "enabled": os.getenv("ZIPRECRUITER_ENABLED", "false").lower() == "true",
            "api_key": os.getenv("ZIPRECRUITER_API_KEY"),
            "endpoint": "https://api.ziprecruiter.com/v1/jobs"
        },
        "glassdoor": {
            "enabled": os.getenv("GLASSDOOR_ENABLED", "false").lower() == "true",
            "partner_id": os.getenv("GLASSDOOR_PARTNER_ID"),
            "api_key": os.getenv("GLASSDOOR_API_KEY"),
            "endpoint": "https://api.glassdoor.com/api/v1/jobs"
        },
        "careerbuilder": {
            "enabled": os.getenv("CAREERBUILDER_ENABLED", "false").lower() == "true",
            "api_key": os.getenv("CAREERBUILDER_API_KEY"),
            "endpoint": "https://api.careerbuilder.com/v2/jobs"
        },
        "monster": {
            "enabled": os.getenv("MONSTER_ENABLED", "false").lower() == "true",
            "api_key": os.getenv("MONSTER_API_KEY"),
            "endpoint": "https://api.monster.com/v1/jobs"
        },
        "simplyhired": {
            "enabled": os.getenv("SIMPLYHIRED_ENABLED", "false").lower() == "true",
            "api_key": os.getenv("SIMPLYHIRED_API_KEY"),
            "endpoint": "https://api.simplyhired.com/v1/jobs"
        }
    }


# ==========================================================
# LINKEDIN API
# ==========================================================

class LinkedInPoster:
    """LinkedIn Job Posting API Integration"""
    
    BASE_URL = "https://api.linkedin.com/rest"
    
    def __init__(self, config: Dict):
        self.config = config
        self.headers = {
            "Authorization": f"Bearer {config['access_token']}",
            "X-Restli-Protocol-Version": "2.0.0",
            "Content-Type": "application/json",
            "LinkedIn-Version": config.get("api_version", "202401")
        }
    
    def is_configured(self) -> bool:
        return all([
            self.config.get("access_token"),
            self.config.get("organization_id")
        ])
    
    def _build_job_payload(self, job: JobPostData) -> Dict:
        """Build LinkedIn job posting payload"""
        # Format employment type for LinkedIn
        employment_type_map = {
            "Contract": "CONTRACT",
            "Contract to Hire": "CONTRACT_TO_HIRE",
            "Full Time": "FULL_TIME",
            "Part Time": "PART_TIME"
        }
        
        # Format location
        location_parts = job.location.split(",")
        city = location_parts[0].strip() if location_parts else ""
        state = location_parts[1].strip() if len(location_parts) > 1 else ""
        
        # Build description with skills
        full_description = job.description
        if job.skills:
            full_description += f"\n\nRequired Skills: {', '.join(job.skills)}"
        if job.experience:
            full_description += f"\n\nExperience: {job.experience}"
        if job.work_authorization and job.work_authorization != "Any":
            full_description += f"\n\nWork Authorization: {job.work_authorization}"
        
        payload = {
            "author": f"urn:li:organization:{self.config['organization_id']}",
            "externalJobPostingId": job.job_id,
            "title": job.title,
            "description": {
                "text": full_description
            },
            "employmentStatus": employment_type_map.get(job.employment_type, "CONTRACT"),
            "location": f"{job.location}, United States",
            "listedAt": int(datetime.now().timestamp() * 1000),
            "apply": {
                "applyMethod": {
                    "externalApply": {
                        "externalApplyUrl": job.apply_url
                    }
                }
            }
        }
        
        # Add salary if available
        if job.salary:
            payload["salary"] = {
                "description": {
                    "text": job.salary
                }
            }
        
        return payload
    
    def post_job(self, job: JobPostData) -> PortalResult:
        """Post job to LinkedIn"""
        if not self.is_configured():
            return PortalResult(
                portal="linkedin",
                status=PortalStatus.SKIPPED,
                error_message="LinkedIn not configured"
            )
        
        try:
            payload = self._build_job_payload(job)
            
            response = requests.post(
                f"{self.BASE_URL}/jobs",
                headers=self.headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code in [200, 201]:
                data = response.json()
                job_urn = data.get("id", "")
                
                # Extract job ID from URN
                external_id = job_urn.split(":")[-1] if job_urn else None
                post_url = f"https://www.linkedin.com/jobs/view/{external_id}" if external_id else None
                
                return PortalResult(
                    portal="linkedin",
                    status=PortalStatus.POSTED,
                    post_url=post_url,
                    external_id=external_id,
                    posted_at=datetime.now().isoformat()
                )
            else:
                error_msg = f"LinkedIn API error: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return PortalResult(
                    portal="linkedin",
                    status=PortalStatus.FAILED,
                    error_message=error_msg
                )
                
        except Exception as e:
            error_msg = f"LinkedIn posting failed: {str(e)}"
            logger.error(error_msg)
            return PortalResult(
                portal="linkedin",
                status=PortalStatus.FAILED,
                error_message=error_msg
            )


# ==========================================================
# INDEED API
# ==========================================================

class IndeedPoster:
    """Indeed Job Posting API Integration"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.endpoint = "https://employers.indeed.com/api/v1/job postings"
    
    def is_configured(self) -> bool:
        return all([
            self.config.get("api_key"),
            self.config.get("secret")
        ])
    
    def _get_access_token(self) -> Optional[str]:
        """Get OAuth access token for Indeed API"""
        try:
            auth_url = "https://apis.indeed.com/oauth/v2/tokens"
            
            response = requests.post(
                auth_url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.config["api_key"),
                    "client_secret": self.config["secret"],
                    "scope": "employer_access"
                },
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json().get("access_token")
            else:
                logger.error(f"Indeed auth failed: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Indeed token request failed: {e}")
            return None
    
    def _build_job_payload(self, job: JobPostData) -> Dict:
        """Build Indeed job posting payload"""
        job_type_map = {
            "Contract": "Contract",
            "Contract to Hire": "Contract",
            "Full Time": "Full-time",
            "Part Time": "Part-time"
        }
        
        payload = {
            "job": {
                "title": job.title,
                "description": {
                    "text": job.description
                },
                "location": {
                    "city": job.location.split(",")[0].strip() if "," in job.location else job.location,
                    "country": "US"
                },
                "jobType": job_type_map.get(job.employment_type, "Contract"),
                "externalApplyLink": job.apply_url,
                "externalId": job.job_id
            }
        }
        
        # Add skills as requirements
        if job.skills:
            payload["job"]["requirements"] = ", ".join(job.skills)
        
        return payload
    
    def post_job(self, job: JobPostData) -> PortalResult:
        """Post job to Indeed"""
        if not self.is_configured():
            return PortalResult(
                portal="indeed",
                status=PortalStatus.SKIPPED,
                error_message="Indeed not configured"
            )
        
        try:
            access_token = self._get_access_token()
            if not access_token:
                return PortalResult(
                    portal="indeed",
                    status=PortalStatus.FAILED,
                    error_message="Failed to get Indeed access token"
                )
            
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            payload = self._build_job_payload(job)
            
            response = requests.post(
                self.endpoint,
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code in [200, 201]:
                data = response.json()
                external_id = data.get("job", {}).get("id")
                
                return PortalResult(
                    portal="indeed",
                    status=PortalStatus.POSTED,
                    post_url=f"https://www.indeed.com/viewjob?jk={external_id}" if external_id else None,
                    external_id=external_id,
                    posted_at=datetime.now().isoformat()
                )
            else:
                error_msg = f"Indeed API error: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return PortalResult(
                    portal="indeed",
                    status=PortalStatus.FAILED,
                    error_message=error_msg
                )
                
        except Exception as e:
            error_msg = f"Indeed posting failed: {str(e)}"
            logger.error(error_msg)
            return PortalResult(
                portal="indeed",
                status=PortalStatus.FAILED,
                error_message=error_msg
            )


# ==========================================================
# ZIPRECRUITER API
# ==========================================================

class ZipRecruiterPoster:
    """ZipRecruiter Job Posting API Integration"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.endpoint = "https://api.ziprecruiter.com/v1/jobs"
    
    def is_configured(self) -> bool:
        return bool(self.config.get("api_key"))
    
    def _build_job_payload(self, job: JobPostData) -> Dict:
        """Build ZipRecruiter job posting payload"""
        job_type_map = {
            "Contract": "contract",
            "Contract to Hire": "contract_to_perm",
            "Full Time": "full_time",
            "Part Time": "part_time"
        }
        
        payload = {
            "job_title": job.title,
            "company_name": job.company,
            "job_description": job.description,
            "city": job.location.split(",")[0].strip() if "," in job.location else job.location,
            "state": job.location.split(",")[1].strip() if "," in job.location else "",
            "country": "US",
            "job_type": job_type_map.get(job.employment_type, "contract"),
            "apply_url": job.apply_url,
            "external_id": job.job_id
        }
        
        if job.salary:
            payload["salary_description"] = job.salary
        
        return payload
    
    def post_job(self, job: JobPostData) -> PortalResult:
        """Post job to ZipRecruiter"""
        if not self.is_configured():
            return PortalResult(
                portal="ziprecruiter",
                status=PortalStatus.SKIPPED,
                error_message="ZipRecruiter not configured"
            )
        
        try:
            headers = {
                "Authorization": f"Bearer {self.config['api_key']}",
                "Content-Type": "application/json"
            }
            
            payload = self._build_job_payload(job)
            
            response = requests.post(
                self.endpoint,
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code in [200, 201]:
                data = response.json()
                external_id = data.get("job_id")
                
                return PortalResult(
                    portal="ziprecruiter",
                    status=PortalStatus.POSTED,
                    post_url=data.get("job_url"),
                    external_id=external_id,
                    posted_at=datetime.now().isoformat()
                )
            else:
                error_msg = f"ZipRecruiter API error: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return PortalResult(
                    portal="ziprecruiter",
                    status=PortalStatus.FAILED,
                    error_message=error_msg
                )
                
        except Exception as e:
            error_msg = f"ZipRecruiter posting failed: {str(e)}"
            logger.error(error_msg)
            return PortalResult(
                portal="ziprecruiter",
                status=PortalStatus.FAILED,
                error_message=error_msg
            )


# ==========================================================
# GLASSDOOR API
# ==========================================================

class GlassdoorPoster:
    """Glassdoor Job Posting API Integration"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.endpoint = "https://api.glassdoor.com/api/v1/jobs"
    
    def is_configured(self) -> bool:
        return all([
            self.config.get("partner_id"),
            self.config.get("api_key")
        ])
    
    def _build_job_payload(self, job: JobPostData) -> Dict:
        """Build Glassdoor job posting payload"""
        job_type_map = {
            "Contract": "Contract",
            "Contract to Hire": "Contract",
            "Full Time": "Full-time",
            "Part Time": "Part-time"
        }
        
        payload = {
            "partnerId": self.config["partner_id"],
            "key": self.config["api_key"],
            "action": "addJob",
            "jobTitle": job.title,
            "employerName": job.company,
            "jobDescription": job.description,
            "location": job.location,
            "jobType": job_type_map.get(job.employment_type, "Contract"),
            "applyUrl": job.apply_url,
            "jobFunction": "Information Technology"
        }
        
        return payload
    
    def post_job(self, job: JobPostData) -> PortalResult:
        """Post job to Glassdoor"""
        if not self.is_configured():
            return PortalResult(
                portal="glassdoor",
                status=PortalStatus.SKIPPED,
                error_message="Glassdoor not configured"
            )
        
        try:
            payload = self._build_job_payload(job)
            
            response = requests.post(
                self.endpoint,
                data=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get("success"):
                    external_id = data.get("jobId")
                    
                    return PortalResult(
                        portal="glassdoor",
                        status=PortalStatus.POSTED,
                        post_url=f"https://www.glassdoor.com/job/{external_id}" if external_id else None,
                        external_id=external_id,
                        posted_at=datetime.now().isoformat()
                    )
                else:
                    error_msg = f"Glassdoor API error: {data.get('message', 'Unknown error')}"
                    logger.error(error_msg)
                    return PortalResult(
                        portal="glassdoor",
                        status=PortalStatus.FAILED,
                        error_message=error_msg
                    )
            else:
                error_msg = f"Glassdoor API error: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return PortalResult(
                    portal="glassdoor",
                    status=PortalStatus.FAILED,
                    error_message=error_msg
                )
                
        except Exception as e:
            error_msg = f"Glassdoor posting failed: {str(e)}"
            logger.error(error_msg)
            return PortalResult(
                portal="glassdoor",
                status=PortalStatus.FAILED,
                error_message=error_msg
            )


# ==========================================================
# CAREERBUILDER API
# ==========================================================

class CareerBuilderPoster:
    """CareerBuilder Job Posting API Integration"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.endpoint = "https://api.careerbuilder.com/v2/jobs"
    
    def is_configured(self) -> bool:
        return bool(self.config.get("api_key"))
    
    def _build_job_payload(self, job: JobPostData) -> Dict:
        """Build CareerBuilder job posting payload"""
        job_type_map = {
            "Contract": "JTCT",
            "Contract to Hire": "JTCT",
            "Full Time": "JTFT",
            "Part Time": "JTPT"
        }
        
        payload = {
            "Job": {
                "Title": job.title,
                "Description": job.description,
                "City": job.location.split(",")[0].strip() if "," in job.location else job.location,
                "State": job.location.split(",")[1].strip() if "," in job.location else "",
                "Country": "US",
                "JobType": job_type_map.get(job.employment_type, "JTCT"),
                "ApplyURL": job.apply_url,
                "ExternalID": job.job_id
            }
        }
        
        return payload
    
    def post_job(self, job: JobPostData) -> PortalResult:
        """Post job to CareerBuilder"""
        if not self.is_configured():
            return PortalResult(
                portal="careerbuilder",
                status=PortalStatus.SKIPPED,
                error_message="CareerBuilder not configured"
            )
        
        try:
            headers = {
                "Authorization": f"Bearer {self.config['api_key']}",
                "Content-Type": "application/json"
            }
            
            payload = self._build_job_payload(job)
            
            response = requests.post(
                self.endpoint,
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code in [200, 201]:
                data = response.json()
                external_id = data.get("Job", {}).get("DID")
                
                return PortalResult(
                    portal="careerbuilder",
                    status=PortalStatus.POSTED,
                    post_url=f"https://www.careerbuilder.com/job/{external_id}" if external_id else None,
                    external_id=external_id,
                    posted_at=datetime.now().isoformat()
                )
            else:
                error_msg = f"CareerBuilder API error: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return PortalResult(
                    portal="careerbuilder",
                    status=PortalStatus.FAILED,
                    error_message=error_msg
                )
                
        except Exception as e:
            error_msg = f"CareerBuilder posting failed: {str(e)}"
            logger.error(error_msg)
            return PortalResult(
                portal="careerbuilder",
                status=PortalStatus.FAILED,
                error_message=error_msg
            )


# ==========================================================
# MONSTER API
# ==========================================================

class MonsterPoster:
    """Monster Job Posting API Integration"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.endpoint = "https://api.monster.com/v1/jobs"
    
    def is_configured(self) -> bool:
        return bool(self.config.get("api_key"))
    
    def _build_job_payload(self, job: JobPostData) -> Dict:
        """Build Monster job posting payload"""
        job_type_map = {
            "Contract": "Contract",
            "Contract to Hire": "Contract",
            "Full Time": "Full Time",
            "Part Time": "Part Time"
        }
        
        payload = {
            "title": job.title,
            "description": job.description,
            "company": job.company,
            "location": {
                "city": job.location.split(",")[0].strip() if "," in job.location else job.location,
                "country": "US"
            },
            "jobType": job_type_map.get(job.employment_type, "Contract"),
            "applyUrl": job.apply_url,
            "externalId": job.job_id
        }
        
        return payload
    
    def post_job(self, job: JobPostData) -> PortalResult:
        """Post job to Monster"""
        if not self.is_configured():
            return PortalResult(
                portal="monster",
                status=PortalStatus.SKIPPED,
                error_message="Monster not configured"
            )
        
        try:
            headers = {
                "Authorization": f"Bearer {self.config['api_key']}",
                "Content-Type": "application/json"
            }
            
            payload = self._build_job_payload(job)
            
            response = requests.post(
                self.endpoint,
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code in [200, 201]:
                data = response.json()
                external_id = data.get("jobId")
                
                return PortalResult(
                    portal="monster",
                    status=PortalStatus.POSTED,
                    post_url=f"https://www.monster.com/job/{external_id}" if external_id else None,
                    external_id=external_id,
                    posted_at=datetime.now().isoformat()
                )
            else:
                error_msg = f"Monster API error: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return PortalResult(
                    portal="monster",
                    status=PortalStatus.FAILED,
                    error_message=error_msg
                )
                
        except Exception as e:
            error_msg = f"Monster posting failed: {str(e)}"
            logger.error(error_msg)
            return PortalResult(
                portal="monster",
                status=PortalStatus.FAILED,
                error_message=error_msg
            )


# ==========================================================
# SIMPLYHIRED API
# ==========================================================

class SimplyHiredPoster:
    """SimplyHired Job Posting API Integration"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.endpoint = "https://api.simplyhired.com/v1/jobs"
    
    def is_configured(self) -> bool:
        return bool(self.config.get("api_key"))
    
    def _build_job_payload(self, job: JobPostData) -> Dict:
        """Build SimplyHired job posting payload"""
        job_type_map = {
            "Contract": "Contract",
            "Contract to Hire": "Contract",
            "Full Time": "Full-time",
            "Part Time": "Part-time"
        }
        
        payload = {
            "title": job.title,
            "description": job.description,
            "company": job.company,
            "location": job.location,
            "jobType": job_type_map.get(job.employment_type, "Contract"),
            "applyUrl": job.apply_url,
            "externalId": job.job_id
        }
        
        return payload
    
    def post_job(self, job: JobPostData) -> PortalResult:
        """Post job to SimplyHired"""
        if not self.is_configured():
            return PortalResult(
                portal="simplyhired",
                status=PortalStatus.SKIPPED,
                error_message="SimplyHired not configured"
            )
        
        try:
            headers = {
                "Authorization": f"Bearer {self.config['api_key']}",
                "Content-Type": "application/json"
            }
            
            payload = self._build_job_payload(job)
            
            response = requests.post(
                self.endpoint,
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code in [200, 201]:
                data = response.json()
                external_id = data.get("jobId")
                
                return PortalResult(
                    portal="simplyhired",
                    status=PortalStatus.POSTED,
                    post_url=data.get("jobUrl"),
                    external_id=external_id,
                    posted_at=datetime.now().isoformat()
                )
            else:
                error_msg = f"SimplyHired API error: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return PortalResult(
                    portal="simplyhired",
                    status=PortalStatus.FAILED,
                    error_message=error_msg
                )
                
        except Exception as e:
            error_msg = f"SimplyHired posting failed: {str(e)}"
            logger.error(error_msg)
            return PortalResult(
                portal="simplyhired",
                status=PortalStatus.FAILED,
                error_message=error_msg
            )


# ==========================================================
# DATABASE INTEGRATION
# ==========================================================

class JobDistributionDB:
    """Database operations for job distribution tracking"""
    
    def __init__(self, db_connection=None):
        self.db = db_connection
    
    def save_distribution_results(self, job_id: str, results: List[PortalResult]) -> bool:
        """Save distribution results to database"""
        try:
            # This is a placeholder - implement based on your actual DB schema
            # Example SQL:
            # INSERT INTO job_distributions (job_id, portal, status, post_url, external_id, posted_at, error_message)
            # VALUES (?, ?, ?, ?, ?, ?, ?)
            
            for result in results:
                logger.info(f"Saving distribution result for {job_id} on {result.portal}: {result.status.value}")
                # Implement actual DB insert here
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to save distribution results: {e}")
            return False
    
    def update_job_status(self, job_id: str, distribution_status: str) -> bool:
        """Update job posting status in database"""
        try:
            # Example SQL:
            # UPDATE jobs SET distribution_status = ?, distributed_at = NOW() WHERE jobid = ?
            logger.info(f"Updating job {job_id} distribution status to: {distribution_status}")
            # Implement actual DB update here
            return True
            
        except Exception as e:
            logger.error(f"Failed to update job status: {e}")
            return False
    
    def get_distribution_history(self, job_id: str) -> List[Dict]:
        """Get distribution history for a job"""
        try:
            # Example SQL:
            # SELECT * FROM job_distributions WHERE job_id = ? ORDER BY posted_at DESC
            return []
            
        except Exception as e:
            logger.error(f"Failed to get distribution history: {e}")
            return []


# ==========================================================
# MAIN DISTRIBUTION ORCHESTRATOR
# ==========================================================

class JobDistributor:
    """Main orchestrator for job distribution to all portals"""
    
    def __init__(self, db_connection=None):
        self.config = get_portal_config()
        self.db = JobDistributionDB(db_connection)
        
        # Initialize all portal posters
        self.posters = {
            "linkedin": LinkedInPoster(self.config["linkedin"]),
            "indeed": IndeedPoster(self.config["indeed"]),
            "ziprecruiter": ZipRecruiterPoster(self.config["ziprecruiter"]),
            "glassdoor": GlassdoorPoster(self.config["glassdoor"]),
            "careerbuilder": CareerBuilderPoster(self.config["careerbuilder"]),
            "monster": MonsterPoster(self.config["monster"]),
            "simplyhired": SimplyHiredPoster(self.config["simplyhired"])
        }
    
    def distribute_job(self, job: dict, portals: Optional[List[str]] = None) -> Dict:
        """
        Distribute a job to specified job portals
        
        Args:
            job: Job dictionary from your system
            portals: List of portal names to post to (None = all enabled)
        
        Returns:
            Dictionary with distribution results
        """
        # Convert to standardized format
        job_data = JobPostData.from_job_dict(job)
        
        # Determine which portals to use
        target_portals = portals or list(self.posters.keys())
        
        results = []
        posted_count = 0
        failed_count = 0
        skipped_count = 0
        
        logger.info(f"Starting job distribution for {job_data.title} (ID: {job_data.job_id})")
        logger.info(f"Target portals: {target_portals}")
        
        for portal_name in target_portals:
            poster = self.posters.get(portal_name)
            
            if not poster:
                logger.warning(f"Unknown portal: {portal_name}")
                continue
            
            # Check if portal is enabled
            if not self.config.get(portal_name, {}).get("enabled", False):
                logger.info(f"Portal {portal_name} is disabled, skipping")
                results.append(PortalResult(
                    portal=portal_name,
                    status=PortalStatus.SKIPPED,
                    error_message="Portal disabled in configuration"
                ))
                skipped_count += 1
                continue
            
            # Post to portal
            logger.info(f"Posting to {portal_name}...")
            result = poster.post_job(job_data)
            results.append(result)
            
            if result.status == PortalStatus.POSTED:
                posted_count += 1
                logger.info(f"Successfully posted to {portal_name}: {result.post_url}")
            elif result.status == PortalStatus.FAILED:
                failed_count += 1
                logger.error(f"Failed to post to {portal_name}: {result.error_message}")
            else:
                skipped_count += 1
        
        # Save results to database
        self.db.save_distribution_results(job_data.job_id, results)
        
        # Update job status
        distribution_status = "completed" if posted_count > 0 else "failed"
        self.db.update_job_status(job_data.job_id, distribution_status)
        
        # Build response
        response = {
            "success": posted_count > 0,
            "job_id": job_data.job_id,
            "summary": {
                "total": len(target_portals),
                "posted": posted_count,
                "failed": failed_count,
                "skipped": skipped_count
            },
            "results": [
                {
                    "portal": r.portal,
                    "status": r.status.value,
                    "post_url": r.post_url,
                    "external_id": r.external_id,
                    "posted_at": r.posted_at,
                    "error_message": r.error_message
                }
                for r in results
            ]
        }
        
        logger.info(f"Job distribution completed for {job_data.job_id}")
        return response
    
    def get_portal_status(self) -> Dict:
        """Get configuration status of all portals"""
        status = {}
        
        for name, poster in self.posters.items():
            config = self.config.get(name, {})
            status[name] = {
                "enabled": config.get("enabled", False),
                "configured": poster.is_configured()
            }
        
        return status


# ==========================================================
# INTEGRATION WITH EMAIL SENDER
# ==========================================================

def distribute_job_after_notification(job: dict, db_connection=None) -> Dict:
    """
    Main entry point - distribute job after email notification is sent
    
    This function should be called after send_job_notification() succeeds
    
    Args:
        job: Job dictionary with all job details
        db_connection: Optional database connection for tracking
    
    Returns:
        Distribution results dictionary
    """
    distributor = JobDistributor(db_connection)
    return distributor.distribute_job(job)


def distribute_job_with_notification(job: dict, db_connection=None) -> Dict:
    """
    Complete workflow: Send email notification AND distribute to job portals
    
    Args:
        job: Job dictionary with all job details
        db_connection: Optional database connection
    
    Returns:
        Combined results dictionary
    """
    from email_sender import send_job_notification
    
    results = {
        "job_id": job.get("jobid"),
        "email_sent": False,
        "distribution": None,
        "errors": []
    }
    
    # Step 1: Send email notification
    logger.info(f"Sending email notification for job {job.get('jobid')}...")
    email_success = send_job_notification(job)
    results["email_sent"] = email_success
    
    if not email_success:
        error_msg = "Email notification failed"
        logger.error(error_msg)
        results["errors"].append(error_msg)
        # Continue with distribution even if email fails
    
    # Step 2: Distribute to job portals
    logger.info(f"Starting job distribution for job {job.get('jobid')}...")
    distribution_results = distribute_job_after_notification(job, db_connection)
    results["distribution"] = distribution_results
    
    if not distribution_results.get("success"):
        error_msg = "Job distribution failed on all portals"
        logger.error(error_msg)
        results["errors"].append(error_msg)
    
    results["success"] = email_success or distribution_results.get("success", False)
    
    return results


# ==========================================================
# UTILITY FUNCTIONS
# ==========================================================

def get_enabled_portals() -> List[str]:
    """Get list of enabled and configured portals"""
    config = get_portal_config()
    distributor = JobDistributor()
    
    enabled = []
    for name, poster in distributor.posters.items():
        if config.get(name, {}).get("enabled", False) and poster.is_configured():
            enabled.append(name)
    
    return enabled


def validate_portal_config() -> Dict:
    """Validate all portal configurations"""
    config = get_portal_config()
    distributor = JobDistributor()
    
    validation = {}
    for name, poster in distributor.posters.items():
        portal_config = config.get(name, {})
        validation[name] = {
            "enabled": portal_config.get("enabled", False),
            "configured": poster.is_configured(),
            "ready": portal_config.get("enabled", False) and poster.is_configured()
        }
    
    return validation


# ==========================================================
# TEST / DEBUG
# ==========================================================

if __name__ == "__main__":
    # Test configuration
    print("=" * 60)
    print("JOB DISTRIBUTION MODULE - CONFIGURATION TEST")
    print("=" * 60)
    
    validation = validate_portal_config()
    
    for portal, status in validation.items():
        print(f"\n{portal.upper()}:")
        print(f"  Enabled: {status['enabled']}")
        print(f"  Configured: {status['configured']}")
        print(f"  Ready: {status['ready']}")
    
    print("\n" + "=" * 60)
    print(f"Ready portals: {[p for p, s in validation.items() if s['ready']]}")
    print("=" * 60)
