from fastapi import APIRouter, Query, Depends, HTTPException
from typing import List, Optional
from core.schemas.course_schema import (
    CourseResponse, CourseSearchParams, CourseUpdate
)
from services.course_service import CourseService
from utils.exceptions import ResourceNotFoundException

router = APIRouter()
course_service = CourseService()


@router.get("", response_model=List[CourseResponse])
async def search_courses(
    term: Optional[str] = Query(None, description="Term code (e.g., 1258)"),
    subject: Optional[str] = Query(None, description="Subject/department code"),
    catalog_number: Optional[str] = Query(None, description="Course number"),
    keyword: Optional[str] = Query(None, description="Search keyword"),
    instructor: Optional[str] = Query(None, description="Instructor name"),
    ge_attribute: Optional[str] = Query(None, description="General education attribute"),
    has_seats: Optional[bool] = Query(None, description="Only show courses with available seats"),
    instruction_mode: Optional[str] = Query(None, description="Instruction mode"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip")
):
    """
    Search for courses with various filters
    """
    search_params = CourseSearchParams(
        term=term,
        subject=subject,
        catalog_number=catalog_number,
        keyword=keyword,
        instructor=instructor,
        ge_attribute=ge_attribute,
        has_seats=has_seats,
        instruction_mode=instruction_mode
    )
    
    courses = await course_service.search_courses(search_params, limit, offset)
    return courses


@router.get("/{class_nbr}", response_model=CourseResponse)
async def get_course(class_nbr: int):
    """
    Get a specific course by class number
    """
    course = await course_service.get_course_by_class_nbr(class_nbr)
    if not course:
        raise ResourceNotFoundException("Course", class_nbr)
    return course


@router.get("/subject/{subject}/catalog/{catalog_nbr}", response_model=List[CourseResponse])
async def get_courses_by_code(subject: str, catalog_nbr: str):
    """
    Get all sections of a course by subject and catalog number
    """
    courses = await course_service.get_courses_by_code(subject.upper(), catalog_nbr)
    if not courses:
        raise ResourceNotFoundException("Course", f"{subject} {catalog_nbr}")
    return courses


@router.post("/sync-from-sis")
async def sync_courses_from_sis(
    term: str = Query(..., description="Term to sync (e.g., 1258)"),
    subject: Optional[str] = Query(None, description="Specific subject to sync")
):
    """
    Sync courses from the SIS API to the database
    """
    result = await course_service.sync_courses_from_sis(term, subject)
    return result


@router.patch("/{class_nbr}", response_model=CourseResponse)
async def update_course(class_nbr: int, course_update: CourseUpdate):
    """
    Update course information
    """
    course = await course_service.update_course(class_nbr, course_update)
    if not course:
        raise ResourceNotFoundException("Course", class_nbr)
    return course


@router.post("/{class_nbr}/refresh-enrollment")
async def refresh_enrollment(class_nbr: int):
    """
    Refresh enrollment information for a specific course from SIS
    """
    result = await course_service.refresh_enrollment(class_nbr)
    if not result:
        raise ResourceNotFoundException("Course", class_nbr)
    return {"message": "Enrollment information updated successfully"}