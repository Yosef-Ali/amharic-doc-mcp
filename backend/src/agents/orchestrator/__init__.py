"""CrewAI orchestrator for coordinating multi-agent document processing workflows."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from crewai import Agent, Crew, Task, Process
from crewai.tools import BaseTool
from sqlalchemy.ext.asyncio import AsyncSession

from ...db.models.processing_job import ProcessingJob, JobStatus
from ...db.models.processing_task import ProcessingTask, TaskStatus, AgentType
from ...db.models.document import Document
from ...config.settings import Settings

logger = logging.getLogger(__name__)


class DocumentProcessingOrchestrator:
    """Orchestrates document processing using CrewAI multi-agent system."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.agents: Dict[str, Agent] = {}
        self.tools: Dict[str, BaseTool] = {}
        self.active_crews: Dict[str, Crew] = {}
        
        # Initialize agents and tools
        self._initialize_agents()
        self._initialize_tools()
        
    def _initialize_agents(self) -> None:
        """Initialize all specialized agents."""
        
        # Coordinator Agent - manages workflow and task distribution
        self.agents['coordinator'] = Agent(
            role='Document Processing Coordinator',
            goal='Coordinate document processing workflow and ensure quality outcomes',
            backstory="""You are an expert document processing coordinator with deep knowledge
            of Amharic language processing, OCR technologies, and quality assurance. Your role
            is to analyze incoming documents, determine the optimal processing strategy, and
            coordinate other agents to achieve the best results.""",
            verbose=True,
            allow_delegation=True,
            max_iter=5,
            memory=True
        )
        
        # Document Analyzer - analyzes document type and structure
        self.agents['document_analyzer'] = Agent(
            role='Document Structure Analyzer',
            goal='Analyze document structure, format, and complexity to determine processing approach',
            backstory="""You are a specialist in document analysis with expertise in various
            document formats (PDF, images, Word documents, CSV files). You can identify
            document types, assess quality, detect layout patterns, and recommend optimal
            processing strategies.""",
            verbose=True,
            allow_delegation=False,
            max_iter=3,
            memory=True
        )
        
        # OCR Specialist - handles text extraction from images and PDFs
        self.agents['ocr_specialist'] = Agent(
            role='OCR Processing Specialist',
            goal='Extract text from images and scanned documents with maximum accuracy',
            backstory="""You are an OCR specialist with deep expertise in Amharic text
            recognition. You understand the nuances of Ethiopian scripts, various fonts,
            and can optimize OCR parameters for different document qualities and layouts.""",
            verbose=True,
            allow_delegation=False,
            max_iter=3,
            memory=True
        )
        
        # Amharic NLP Agent - processes Amharic text
        self.agents['amharic_nlp'] = Agent(
            role='Amharic Language Processing Expert',
            goal='Process and analyze Amharic text for entity recognition, spell checking, and summarization',
            backstory="""You are an expert in Amharic natural language processing with
            deep understanding of Ethiopian languages, morphology, and cultural context.
            You can perform entity recognition, spell checking, text normalization,
            and generate meaningful summaries.""",
            verbose=True,
            allow_delegation=False,
            max_iter=4,
            memory=True
        )
        
        # Quality Assurance Agent - validates processing results
        self.agents['quality_assurance'] = Agent(
            role='Quality Assurance Specialist',
            goal='Validate processing results and ensure they meet quality standards',
            backstory="""You are a quality assurance specialist with expertise in
            evaluating OCR accuracy, text processing quality, and overall document
            processing outcomes. You can identify issues, suggest improvements,
            and ensure compliance with quality thresholds.""",
            verbose=True,
            allow_delegation=False,
            max_iter=3,
            memory=True
        )
        
        # Export Specialist - handles document export and formatting
        self.agents['export_specialist'] = Agent(
            role='Document Export Specialist',
            goal='Generate high-quality exports in various formats maintaining original structure',
            backstory="""You are an expert in document formatting and export with deep
            knowledge of various output formats (PDF, DOCX, HTML, Markdown, JSON).
            You can preserve document structure, apply templates, and ensure exports
            meet specific requirements and maintain readability.""",
            verbose=True,
            allow_delegation=False,
            max_iter=3,
            memory=True
        )
        
        logger.info(f"Initialized {len(self.agents)} specialized agents")
        
    def _initialize_tools(self) -> None:
        """Initialize tools that agents can use."""
        
        # OCR Tool
        class OCRTool(BaseTool):
            name = "ocr_processor"
            description = "Extract text from images and scanned documents using Tesseract"
            
            def _run(self, image_path: str, language: str = "amh") -> str:
                try:
                    import pytesseract
                    from PIL import Image
                    
                    # Configure Tesseract for Amharic
                    config = f'--oem 3 --psm 6 -l {language}'
                    
                    # Process image
                    image = Image.open(image_path)
                    text = pytesseract.image_to_string(image, config=config)
                    
                    return text.strip()
                except Exception as e:
                    return f"OCR processing failed: {str(e)}"
                    
            async def _arun(self, image_path: str, language: str = "amh") -> str:
                return self._run(image_path, language)
                
        # Text Analysis Tool
        class TextAnalysisTool(BaseTool):
            name = "text_analyzer"
            description = "Analyze Amharic text for entities, structure, and quality"
            
            def _run(self, text: str, analysis_type: str = "full") -> Dict[str, Any]:
                try:
                    result = {
                        "length": len(text),
                        "word_count": len(text.split()),
                        "has_amharic": any('\u1200' <= char <= '\u137F' for char in text),
                        "analysis_type": analysis_type
                    }
                    
                    if analysis_type == "full":
                        # Basic entity extraction (simplified)
                        entities = []
                        for word in text.split():
                            if '\u1200' <= word[0] <= '\u137F' if word else False:
                                entities.append({
                                    "text": word,
                                    "type": "AMHARIC_ENTITY",
                                    "confidence": 0.8
                                })
                        result["entities"] = entities[:10]  # Limit entities
                        
                    return result
                except Exception as e:
                    return {"error": str(e)}
                    
            async def _arun(self, text: str, analysis_type: str = "full") -> Dict[str, Any]:
                return self._run(text, analysis_type)
                
        # Quality Checker Tool
        class QualityCheckerTool(BaseTool):
            name = "quality_checker"
            description = "Check quality of processed text and provide scores"
            
            def _run(self, original_text: str, processed_text: str) -> Dict[str, Any]:
                try:
                    # Simple quality metrics
                    orig_words = set(original_text.lower().split())
                    proc_words = set(processed_text.lower().split())
                    
                    if orig_words:
                        recall = len(orig_words.intersection(proc_words)) / len(orig_words)
                    else:
                        recall = 0.0
                        
                    if proc_words:
                        precision = len(orig_words.intersection(proc_words)) / len(proc_words)
                    else:
                        precision = 0.0
                        
                    f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
                    
                    return {
                        "precision": precision,
                        "recall": recall,
                        "f1_score": f1_score,
                        "quality_grade": "excellent" if f1_score > 0.9 else "good" if f1_score > 0.7 else "fair" if f1_score > 0.5 else "poor"
                    }
                except Exception as e:
                    return {"error": str(e)}
                    
            async def _arun(self, original_text: str, processed_text: str) -> Dict[str, Any]:
                return self._run(original_text, processed_text)
                
        # Register tools
        self.tools['ocr_processor'] = OCRTool()
        self.tools['text_analyzer'] = TextAnalysisTool()
        self.tools['quality_checker'] = QualityCheckerTool()
        
        logger.info(f"Initialized {len(self.tools)} specialized tools")
        
    async def orchestrate_document_processing(
        self,
        session: AsyncSession,
        job: ProcessingJob,
        document: Document
    ) -> Dict[str, Any]:
        """Orchestrate complete document processing workflow."""
        try:
            logger.info(f"Starting orchestration for job {job.id}")
            
            # Create crew based on document type and requirements
            crew = self._create_processing_crew(job.job_type, document)
            
            # Create tasks for the crew
            tasks = self._create_processing_tasks(job, document)
            
            # Execute crew with error recovery
            result = await self._execute_crew_with_monitoring(
                crew, tasks, job, session
            )
            
            logger.info(f"Orchestration completed for job {job.id}")
            return result
            
        except Exception as e:
            logger.error(f"Orchestration failed for job {job.id}: {e}")
            return {
                "success": False,
                "error": str(e),
                "job_id": str(job.id)
            }
            
    def _create_processing_crew(self, job_type: str, document: Document) -> Crew:
        """Create a crew tailored to the specific processing requirements."""
        
        if job_type == "document_analysis":
            # Crew for document analysis and structure extraction
            crew_agents = [
                self.agents['coordinator'],
                self.agents['document_analyzer'],
                self.agents['quality_assurance']
            ]
            
        elif job_type == "ocr_processing":
            # Crew for OCR text extraction
            crew_agents = [
                self.agents['coordinator'],
                self.agents['ocr_specialist'],
                self.agents['quality_assurance']
            ]
            
        elif job_type == "nlp_processing":
            # Crew for Amharic NLP processing
            crew_agents = [
                self.agents['coordinator'],
                self.agents['amharic_nlp'],
                self.agents['quality_assurance']
            ]
            
        elif job_type == "full_processing":
            # Complete processing crew with all specialists
            crew_agents = [
                self.agents['coordinator'],
                self.agents['document_analyzer'],
                self.agents['ocr_specialist'],
                self.agents['amharic_nlp'],
                self.agents['quality_assurance'],
                self.agents['export_specialist']
            ]
            
        else:
            # Default crew for unknown job types
            crew_agents = [
                self.agents['coordinator'],
                self.agents['document_analyzer'],
                self.agents['quality_assurance']
            ]
            
        # Assign tools to agents
        for agent in crew_agents:
            agent.tools = list(self.tools.values())
            
        # Create crew with hierarchical process
        crew = Crew(
            agents=crew_agents,
            tasks=[],  # Tasks will be added later
            process=Process.hierarchical,
            manager_llm="gpt-4",  # Use GPT-4 for coordination
            verbose=True,
            memory=True,
            max_rpm=30,  # Rate limiting
            embedder={
                "provider": "openai",
                "config": {
                    "model": "text-embedding-ada-002"
                }
            }
        )
        
        return crew
        
    def _create_processing_tasks(
        self,
        job: ProcessingJob,
        document: Document
    ) -> List[Task]:
        """Create tasks for the processing crew."""
        tasks = []
        
        # Document Analysis Task
        analysis_task = Task(
            description=f"""Analyze the document '{document.filename}' to determine:
            1. Document type and format
            2. Content structure and layout
            3. Language detection and text regions
            4. Processing complexity assessment
            5. Quality indicators and potential issues
            
            Document details:
            - Filename: {document.filename}
            - Content Type: {document.content_type}
            - File Size: {document.file_size} bytes
            - Status: {document.status}
            
            Provide a comprehensive analysis with processing recommendations.""",
            agent=self.agents['document_analyzer'],
            expected_output="Detailed document analysis report with processing recommendations",
            tools=list(self.tools.values())
        )
        tasks.append(analysis_task)
        
        # OCR Processing Task (if needed)
        if job.job_type in ["ocr_processing", "full_processing"]:
            ocr_task = Task(
                description=f"""Extract text from the document using OCR technology:
                1. Apply appropriate OCR configuration for document type
                2. Use Amharic language support for Ethiopian text
                3. Preserve document structure and formatting
                4. Validate extraction quality and confidence scores
                5. Handle multiple columns, tables, and complex layouts
                
                Focus on achieving >95% accuracy for clear Amharic text.""",
                agent=self.agents['ocr_specialist'],
                expected_output="Extracted text with confidence scores and quality metrics",
                tools=list(self.tools.values()),
                context=[analysis_task]
            )
            tasks.append(ocr_task)
            
        # NLP Processing Task (if needed)
        if job.job_type in ["nlp_processing", "full_processing"]:
            nlp_task = Task(
                description=f"""Process the extracted Amharic text for:
                1. Named entity recognition (people, places, organizations)
                2. Text normalization and spell checking
                3. Language identification and script validation
                4. Text summarization and key point extraction
                5. Morphological analysis for Amharic text
                
                Ensure cultural context awareness for Ethiopian content.""",
                agent=self.agents['amharic_nlp'],
                expected_output="Processed text with entities, summary, and linguistic analysis",
                tools=list(self.tools.values()),
                context=tasks  # Depends on previous tasks
            )
            tasks.append(nlp_task)
            
        # Quality Assurance Task
        qa_task = Task(
            description=f"""Validate the processing results for quality and accuracy:
            1. Check OCR accuracy against quality thresholds
            2. Validate entity recognition results
            3. Verify text structure preservation
            4. Assess overall processing quality scores
            5. Identify any issues requiring manual review
            
            Apply strict quality standards for production use.""",
            agent=self.agents['quality_assurance'],
            expected_output="Quality assessment report with pass/fail recommendations",
            tools=list(self.tools.values()),
            context=tasks  # Review all previous work
        )
        tasks.append(qa_task)
        
        # Export Task (if full processing)
        if job.job_type == "full_processing":
            export_task = Task(
                description=f"""Generate export-ready outputs in multiple formats:
                1. Create searchable PDF with original layout
                2. Generate structured JSON with metadata
                3. Produce clean text format for further processing
                4. Apply appropriate templates and formatting
                5. Ensure accessibility and compliance standards
                
                Maintain document integrity across all output formats.""",
                agent=self.agents['export_specialist'],
                expected_output="Multiple format exports with consistent formatting",
                tools=list(self.tools.values()),
                context=tasks  # Use all previous results
            )
            tasks.append(export_task)
            
        return tasks
        
    async def _execute_crew_with_monitoring(
        self,
        crew: Crew,
        tasks: List[Task],
        job: ProcessingJob,
        session: AsyncSession
    ) -> Dict[str, Any]:
        """Execute crew with monitoring and error recovery."""
        
        try:
            # Set tasks on crew
            crew.tasks = tasks
            
            # Store active crew for monitoring
            self.active_crews[str(job.id)] = crew
            
            # Execute crew asynchronously
            logger.info(f"Starting crew execution for job {job.id}")
            start_time = datetime.utcnow()
            
            # Run crew (this is synchronous in CrewAI)
            result = await asyncio.get_event_loop().run_in_executor(
                None, crew.kickoff
            )
            
            end_time = datetime.utcnow()
            processing_time = (end_time - start_time).total_seconds()
            
            # Process results
            crew_result = {
                "success": True,
                "result": str(result),
                "processing_time": processing_time,
                "tasks_completed": len(tasks),
                "agents_involved": len(crew.agents),
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat()
            }
            
            logger.info(f"Crew execution completed for job {job.id} in {processing_time:.2f}s")
            
            return crew_result
            
        except Exception as e:
            logger.error(f"Crew execution failed for job {job.id}: {e}")
            
            # Attempt recovery
            recovery_result = await self._attempt_recovery(crew, tasks, job, str(e))
            
            return {
                "success": False,
                "error": str(e),
                "recovery_attempted": True,
                "recovery_result": recovery_result
            }
            
        finally:
            # Clean up active crew
            self.active_crews.pop(str(job.id), None)
            
    async def _attempt_recovery(
        self,
        crew: Crew,
        tasks: List[Task],
        job: ProcessingJob,
        error_message: str
    ) -> Dict[str, Any]:
        """Attempt to recover from crew execution failure."""
        
        logger.info(f"Attempting recovery for job {job.id}")
        
        try:
            # Simplified recovery: create minimal crew with coordinator only
            recovery_crew = Crew(
                agents=[self.agents['coordinator']],
                tasks=[
                    Task(
                        description=f"""Handle the processing error and provide alternative solution:
                        Error: {error_message}
                        
                        Analyze the error and provide:
                        1. Error classification and severity
                        2. Possible causes and solutions
                        3. Alternative processing approach
                        4. Recommendations for manual intervention
                        
                        Focus on providing actionable guidance.""",
                        agent=self.agents['coordinator'],
                        expected_output="Error analysis and recovery recommendations"
                    )
                ],
                process=Process.sequential,
                verbose=True
            )
            
            # Execute recovery crew
            recovery_result = await asyncio.get_event_loop().run_in_executor(
                None, recovery_crew.kickoff
            )
            
            return {
                "success": True,
                "recovery_analysis": str(recovery_result)
            }
            
        except Exception as recovery_error:
            logger.error(f"Recovery failed for job {job.id}: {recovery_error}")
            return {
                "success": False,
                "recovery_error": str(recovery_error)
            }
            
    def get_active_crews(self) -> Dict[str, Dict[str, Any]]:
        """Get information about currently active crews."""
        active_info = {}
        
        for job_id, crew in self.active_crews.items():
            active_info[job_id] = {
                "agent_count": len(crew.agents),
                "task_count": len(crew.tasks),
                "process": crew.process.name if hasattr(crew.process, 'name') else str(crew.process),
                "memory_enabled": crew.memory
            }
            
        return active_info
        
    async def stop_crew(self, job_id: str) -> bool:
        """Stop an active crew (if possible)."""
        crew = self.active_crews.get(job_id)
        if crew:
            # CrewAI doesn't have built-in stop functionality
            # So we remove it from active crews and hope it completes soon
            self.active_crews.pop(job_id, None)
            logger.info(f"Marked crew for job {job_id} for stopping")
            return True
        return False


# Global orchestrator instance
_orchestrator: Optional[DocumentProcessingOrchestrator] = None


def get_document_orchestrator(settings: Settings) -> DocumentProcessingOrchestrator:
    """Get the global document processing orchestrator instance."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = DocumentProcessingOrchestrator(settings)
    return _orchestrator