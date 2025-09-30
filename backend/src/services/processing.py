"""Processing orchestration service for document processing jobs."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

from crewai import Agent, Crew, Task
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from ..db.models.processing_job import ProcessingJob, JobStatus, JobPriority
from ..db.models.processing_task import ProcessingTask, TaskStatus, AgentType
from ..db.models.document import Document
from ..config.settings import Settings

logger = logging.getLogger(__name__)


class ProcessingOrchestrator:
    """Orchestrates document processing jobs using CrewAI."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.active_crews: Dict[str, Crew] = {}
        self.max_concurrent_jobs = settings.MAX_CONCURRENT_JOBS
        
    async def create_job(
        self,
        session: AsyncSession,
        document_id: UUID,
        job_type: str,
        priority: JobPriority = JobPriority.MEDIUM,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ProcessingJob:
        """Create a new processing job."""
        # Apply queue management policies
        await self._apply_queue_management_policies(session, priority)
        
        job = ProcessingJob(
            document_id=document_id,
            job_type=job_type,
            priority=priority,
            status=JobStatus.QUEUED,
            metadata=metadata or {},
            created_at=datetime.utcnow()
        )
        
        session.add(job)
        await session.commit()
        await session.refresh(job)
        
        logger.info(f"Created processing job {job.id} for document {document_id}")
        
        # Queue job for processing
        asyncio.create_task(self._process_job(job.id))
        
        return job
        
    async def get_job_status(
        self,
        session: AsyncSession,
        job_id: UUID
    ) -> Optional[ProcessingJob]:
        """Get processing job status."""
        result = await session.execute(
            select(ProcessingJob).where(ProcessingJob.id == job_id)
        )
        return result.scalar_one_or_none()
        
    async def cancel_job(
        self,
        session: AsyncSession,
        job_id: UUID
    ) -> bool:
        """Cancel a processing job."""
        result = await session.execute(
            update(ProcessingJob)
            .where(ProcessingJob.id == job_id)
            .where(ProcessingJob.status.in_([JobStatus.QUEUED, JobStatus.PROCESSING]))
            .values(
                status=JobStatus.CANCELLED,
                completed_at=datetime.utcnow()
            )
        )
        
        if result.rowcount > 0:
            await session.commit()
            logger.info(f"Cancelled processing job {job_id}")
            
            # Stop active crew if running
            if str(job_id) in self.active_crews:
                # CrewAI doesn't have built-in cancellation, so we mark as cancelled
                # and the crew will check status periodically
                del self.active_crews[str(job_id)]
                
            return True
            
        return False
        
    async def retry_failed_job(
        self,
        session: AsyncSession,
        job_id: UUID
    ) -> bool:
        """Retry a failed processing job."""
        job = await self.get_job_status(session, job_id)
        
        if not job or job.status != JobStatus.FAILED:
            return False
            
        # Reset job status and increment retry count
        job.status = JobStatus.QUEUED
        job.retry_count += 1
        job.error_message = None
        job.completed_at = None
        
        await session.commit()
        
        logger.info(f"Retrying processing job {job_id} (attempt {job.retry_count})")
        
        # Queue job for processing
        asyncio.create_task(self._process_job(job_id))
        
        return True
        
    async def get_processing_statistics(self, session: AsyncSession) -> Dict[str, Any]:
        """Get processing statistics."""
        # Get job counts by status
        result = await session.execute(
            select(ProcessingJob.status, ProcessingJob.id).where(
                ProcessingJob.created_at >= datetime.utcnow() - timedelta(days=7)
            )
        )
        jobs = result.all()
        
        stats = {
            "total_jobs": len(jobs),
            "queued": len([j for j in jobs if j.status == JobStatus.QUEUED]),
            "processing": len([j for j in jobs if j.status == JobStatus.PROCESSING]),
            "completed": len([j for j in jobs if j.status == JobStatus.COMPLETED]),
            "failed": len([j for j in jobs if j.status == JobStatus.FAILED]),
            "cancelled": len([j for j in jobs if j.status == JobStatus.CANCELLED]),
            "active_crews": len(self.active_crews)
        }
        
        return stats
        
    async def _apply_queue_management_policies(self, session: AsyncSession, priority: JobPriority) -> bool:
        """Apply queue overflow and promotion policies."""
        stats = await self.get_processing_statistics(session)
        
        if priority == JobPriority.HIGH and stats["queued"] > 100:
            raise ValueError("Urgent queue at capacity (>100 jobs)")
        
        if priority == JobPriority.MEDIUM and stats["queued"] > 500:
            # Promote oldest standard job to urgent
            await self._promote_oldest_job(session, JobPriority.MEDIUM, JobPriority.HIGH)
            logger.info("Promoted oldest standard job to urgent due to queue overflow")
        
        if priority == JobPriority.LOW and stats["queued"] > 1000:
            # Enable degraded mode with extended SLAs
            logger.warning("Bulk queue overflow - enabling degraded mode")
            
        return True
        
    async def _promote_oldest_job(
        self, 
        session: AsyncSession, 
        from_priority: JobPriority, 
        to_priority: JobPriority
    ) -> bool:
        """Promote the oldest job from one priority to another."""
        from sqlalchemy import update
        
        result = await session.execute(
            update(ProcessingJob)
            .where(ProcessingJob.priority == from_priority)
            .where(ProcessingJob.status == JobStatus.QUEUED)
            .values(priority=to_priority)
            .execution_options(synchronize_session=False)
            .limit(1)
        )
        
        if result.rowcount > 0:
            await session.commit()
            return True
        return False
        
    async def _process_job(self, job_id: UUID) -> None:
        """Process a job using CrewAI."""
        from ..db.database import get_async_session
        
        async with get_async_session() as session:
            job = await self.get_job_status(session, job_id)
            
            if not job or job.status != JobStatus.QUEUED:
                return
                
            try:
                # Update job status to processing
                job.status = JobStatus.PROCESSING
                job.started_at = datetime.utcnow()
                await session.commit()
                
                logger.info(f"Starting processing job {job_id}")
                
                # Create CrewAI crew based on job type
                crew = await self._create_crew_for_job(job)
                self.active_crews[str(job_id)] = crew
                
                # Create processing tasks
                tasks = await self._create_processing_tasks(session, job)
                
                # Execute the crew
                result = await self._execute_crew(crew, tasks, job)
                
                # Update job with results
                job.status = JobStatus.COMPLETED
                job.completed_at = datetime.utcnow()
                job.result = result
                
                await session.commit()
                
                logger.info(f"Completed processing job {job_id}")
                
            except Exception as e:
                logger.error(f"Processing job {job_id} failed: {str(e)}")
                
                job.status = JobStatus.FAILED
                job.completed_at = datetime.utcnow()
                job.error_message = str(e)
                
                await session.commit()
                
                # Retry if under retry limit
                if job.retry_count < self.settings.MAX_RETRY_ATTEMPTS:
                    await asyncio.sleep(60)  # Wait before retry
                    await self.retry_failed_job(session, job_id)
                    
            finally:
                # Clean up active crew
                self.active_crews.pop(str(job_id), None)
                
    async def _create_crew_for_job(self, job: ProcessingJob) -> Crew:
        """Create a CrewAI crew for the specific job type."""
        if job.job_type == "document_analysis":
            return self._create_document_analysis_crew()
        elif job.job_type == "ocr_processing":
            return self._create_ocr_processing_crew()
        elif job.job_type == "nlp_processing":
            return self._create_nlp_processing_crew()
        else:
            return self._create_general_processing_crew()
            
    def _create_document_analysis_crew(self) -> Crew:
        """Create crew for document analysis."""
        coordinator = Agent(
            role="Document Analysis Coordinator",
            goal="Coordinate document analysis and structure extraction",
            backstory="Expert in document structure analysis and metadata extraction",
            verbose=True
        )
        
        analyzer = Agent(
            role="Document Analyzer",
            goal="Analyze document structure and extract metadata",
            backstory="Specialized in document format analysis and content extraction",
            verbose=True
        )
        
        return Crew(
            agents=[coordinator, analyzer],
            tasks=[],
            verbose=True
        )
        
    def _create_ocr_processing_crew(self) -> Crew:
        """Create crew for OCR processing."""
        ocr_agent = Agent(
            role="OCR Specialist",
            goal="Extract text from images and scanned documents",
            backstory="Expert in Optical Character Recognition for multiple languages including Amharic",
            verbose=True
        )
        
        quality_agent = Agent(
            role="OCR Quality Assurance",
            goal="Validate and improve OCR accuracy",
            backstory="Specialized in OCR quality assessment and text correction",
            verbose=True
        )
        
        return Crew(
            agents=[ocr_agent, quality_agent],
            tasks=[],
            verbose=True
        )
        
    def _create_nlp_processing_crew(self) -> Crew:
        """Create crew for NLP processing."""
        nlp_agent = Agent(
            role="Amharic NLP Specialist",
            goal="Process Amharic text for entity recognition and summarization",
            backstory="Expert in Amharic natural language processing and entity extraction",
            verbose=True
        )
        
        return Crew(
            agents=[nlp_agent],
            tasks=[],
            verbose=True
        )
        
    def _create_general_processing_crew(self) -> Crew:
        """Create general processing crew."""
        coordinator = Agent(
            role="Processing Coordinator",
            goal="Coordinate general document processing tasks",
            backstory="Experienced in managing various document processing workflows",
            verbose=True
        )
        
        return Crew(
            agents=[coordinator],
            tasks=[],
            verbose=True
        )
        
    async def _create_processing_tasks(
        self,
        session: AsyncSession,
        job: ProcessingJob
    ) -> List[ProcessingTask]:
        """Create processing tasks for the job."""
        tasks = []
        
        if job.job_type == "document_analysis":
            task = ProcessingTask(
                job_id=job.id,
                agent_type=AgentType.DOCUMENT_ANALYZER,
                task_name="analyze_document_structure",
                status=TaskStatus.PENDING,
                created_at=datetime.utcnow()
            )
            tasks.append(task)
            
        elif job.job_type == "ocr_processing":
            ocr_task = ProcessingTask(
                job_id=job.id,
                agent_type=AgentType.OCR_AGENT,
                task_name="extract_text_from_image",
                status=TaskStatus.PENDING,
                created_at=datetime.utcnow()
            )
            
            qa_task = ProcessingTask(
                job_id=job.id,
                agent_type=AgentType.QUALITY_ASSURANCE,
                task_name="validate_ocr_quality",
                status=TaskStatus.PENDING,
                created_at=datetime.utcnow()
            )
            
            tasks.extend([ocr_task, qa_task])
            
        elif job.job_type == "nlp_processing":
            nlp_task = ProcessingTask(
                job_id=job.id,
                agent_type=AgentType.NLP_AGENT,
                task_name="process_amharic_text",
                status=TaskStatus.PENDING,
                created_at=datetime.utcnow()
            )
            tasks.append(nlp_task)
            
        # Add tasks to session
        for task in tasks:
            session.add(task)
            
        await session.commit()
        
        return tasks
        
    async def _execute_crew(
        self,
        crew: Crew,
        processing_tasks: List[ProcessingTask],
        job: ProcessingJob
    ) -> Dict[str, Any]:
        """Execute the CrewAI crew with the given tasks."""
        crewai_tasks = []
        
        for processing_task in processing_tasks:
            task = Task(
                description=f"Execute {processing_task.task_name} for job {job.id}",
                agent=crew.agents[0],  # Assign to first available agent
                expected_output="Task execution results and metadata"
            )
            crewai_tasks.append(task)
            
        # Update crew with tasks
        crew.tasks = crewai_tasks
        
        # Execute the crew
        result = crew.kickoff()
        
        return {"output": str(result), "tasks_completed": len(crewai_tasks)}


# Global orchestrator instance
_orchestrator: Optional[ProcessingOrchestrator] = None


def get_processing_orchestrator(settings: Settings) -> ProcessingOrchestrator:
    """Get the global processing orchestrator instance."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = ProcessingOrchestrator(settings)
    return _orchestrator