from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from core.schemas.schedule_schema import (
    ScheduleResponse, ScheduleCreate, ScheduleUpdate,
    ScheduleAddCourse, ScheduleRemoveCourse,
    ScheduleValidationResult, ScheduleOptimizationRequest
)
from services.schedule_service import ScheduleService
from utils.exceptions import ResourceNotFoundException, BadRequestException

router = APIRouter()
schedule_service = ScheduleService()


@router.get("", response_model=List[ScheduleResponse])
async def get_schedules(
    user_id: Optional[str] = Query(None, description="User ID to filter schedules"),
    semester: Optional[str] = Query(None, description="Semester to filter schedules")
):
    """
    Get all schedules, optionally filtered by user and semester
    """
    schedules = await schedule_service.get_schedules(user_id, semester)
    return schedules


@router.get("/{schedule_id}", response_model=ScheduleResponse)
async def get_schedule(schedule_id: int):
    """
    Get a specific schedule by ID
    """
    schedule = await schedule_service.get_schedule(schedule_id)
    if not schedule:
        raise ResourceNotFoundException("Schedule", schedule_id)
    return schedule


@router.post("", response_model=ScheduleResponse)
async def create_schedule(schedule_data: ScheduleCreate):
    """
    Create a new schedule
    """
    schedule = await schedule_service.create_schedule(schedule_data)
    return schedule


@router.put("/{schedule_id}", response_model=ScheduleResponse)
async def update_schedule(schedule_id: int, schedule_update: ScheduleUpdate):
    """
    Update schedule information
    """
    schedule = await schedule_service.update_schedule(schedule_id, schedule_update)
    if not schedule:
        raise ResourceNotFoundException("Schedule", schedule_id)
    return schedule


@router.delete("/{schedule_id}")
async def delete_schedule(schedule_id: int):
    """
    Delete a schedule
    """
    result = await schedule_service.delete_schedule(schedule_id)
    if not result:
        raise ResourceNotFoundException("Schedule", schedule_id)
    return {"message": "Schedule deleted successfully"}


@router.post("/{schedule_id}/courses", response_model=ScheduleResponse)
async def add_course_to_schedule(schedule_id: int, course_data: ScheduleAddCourse):
    """
    Add a course to a schedule
    """
    try:
        schedule = await schedule_service.add_course_to_schedule(
            schedule_id, course_data.class_nbr
        )
        return schedule
    except ValueError as e:
        raise BadRequestException(str(e))
    except ResourceNotFoundException:
        raise


@router.delete("/{schedule_id}/courses/{class_nbr}", response_model=ScheduleResponse)
async def remove_course_from_schedule(schedule_id: int, class_nbr: int):
    """
    Remove a course from a schedule
    """
    schedule = await schedule_service.remove_course_from_schedule(schedule_id, class_nbr)
    if not schedule:
        raise ResourceNotFoundException("Schedule", schedule_id)
    return schedule


@router.get("/{schedule_id}/validate", response_model=ScheduleValidationResult)
async def validate_schedule(schedule_id: int):
    """
    Validate a schedule for conflicts and requirements
    """
    result = await schedule_service.validate_schedule(schedule_id)
    if not result:
        raise ResourceNotFoundException("Schedule", schedule_id)
    return result


@router.post("/{schedule_id}/duplicate", response_model=ScheduleResponse)
async def duplicate_schedule(
    schedule_id: int,
    new_name: str = Query(..., description="Name for the duplicated schedule")
):
    """
    Create a copy of an existing schedule
    """
    schedule = await schedule_service.duplicate_schedule(schedule_id, new_name)
    if not schedule:
        raise ResourceNotFoundException("Schedule", schedule_id)
    return schedule


@router.post("/optimize", response_model=ScheduleResponse)
async def optimize_schedule(optimization_request: ScheduleOptimizationRequest):
    """
    Generate an optimized schedule based on requirements and preferences
    """
    try:
        schedule = await schedule_service.optimize_schedule(optimization_request)
        return schedule
    except ValueError as e:
        raise BadRequestException(str(e))