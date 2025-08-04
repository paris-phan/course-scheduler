import os
from google.cloud.sql.connector import Connector
import pg8000
import sqlalchemy
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool
from dotenv import load_dotenv
from contextlib import contextmanager
import hashlib
import json
from datetime import datetime
from typing import Dict, List, Optional, Any

class PostgreSQLClient:
    def __init__(self):
        load_dotenv()
        
        self.connection_name = os.environ.get('CLOUD_SQL_CONNECTION_NAME')
        self.db_user = os.environ.get('POSTGRES_USER')
        self.db_password = os.environ.get('POSTGRES_PASSWORD')
        self.db_name = os.environ.get('POSTGRES_DB')
        self.project_id = os.environ.get('GOOGLE_CLOUD_PROJECT')
        
        if not all([self.connection_name, self.db_user, self.db_password, self.db_name]):
            raise ValueError("Missing required Cloud SQL environment variables: CLOUD_SQL_CONNECTION_NAME, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB")
        
        # Initialize the Cloud SQL connector
        self.connector = Connector()
        
        # Create connection pool
        self.engine = self._create_engine()

    def _create_engine(self):
        """Create SQLAlchemy engine with Cloud SQL connector"""
        def getconn():
            try:
                conn = self.connector.connect(
                    self.connection_name,
                    "pg8000",
                    user=self.db_user,
                    password=self.db_password,
                    db=self.db_name
                )
                return conn
            except Exception as e:
                print(f"Failed to create Cloud SQL connection: {e}")
                raise
        
        # Create connection pool
        engine = create_engine(
            "postgresql+pg8000://",
            creator=getconn,
            poolclass=NullPool,  # Disable connection pooling for Cloud SQL connector
            echo=False,  # Set to True for SQL debugging
        )
        
        return engine

    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = None
        trans = None
        try:
            conn = self.engine.connect()
            trans = conn.begin()
            yield conn
            trans.commit()
        except Exception as e:
            if trans:
                trans.rollback()
            raise e
        finally:
            if conn:
                conn.close()

    def execute_query(self, query: str, params: Dict = None, fetch: bool = False) -> Optional[List[Dict]]:
        """Execute a query and optionally fetch results"""
        with self.get_connection() as conn:
            result = conn.execute(text(query), params or {})
            if fetch:
                return [dict(row._mapping) for row in result]
            return None

    def create_hash(self, data: Dict) -> str:
        """Create a hash for data integrity checking"""
        data_str = json.dumps(data, sort_keys=True)
        return hashlib.sha256(data_str.encode()).hexdigest()

    def upsert_term(self, code: str, name: str, start_date: str = None, end_date: str = None, session: str = 'Regular') -> int:
        """Insert or update a term and return its ID"""
        source_hash = self.create_hash({'code': code, 'name': name, 'session': session})
        
        query = """
        INSERT INTO terms (code, name, start_date, end_date, session, source_hash)
        VALUES (:code, :name, :start_date, :end_date, :session, :source_hash)
        ON CONFLICT (code) DO UPDATE SET
            name = EXCLUDED.name,
            start_date = EXCLUDED.start_date,
            end_date = EXCLUDED.end_date,
            session = EXCLUDED.session,
            source_hash = EXCLUDED.source_hash,
            updated_at = NOW()
        RETURNING id
        """
        
        params = {
            'code': code,
            'name': name,
            'start_date': start_date,
            'end_date': end_date,
            'session': session,
            'source_hash': source_hash
        }
        
        result = self.execute_query(query, params, fetch=True)
        return result[0]['id']

    def upsert_course_catalog(self, subject: str, catalog_number: str, title: str, 
                             description: str = None, min_credits: float = None, 
                             max_credits: float = None, attributes: Dict = None) -> int:
        """Insert or update a course in the catalog and return its ID"""
        source_hash = self.create_hash({
            'subject': subject, 
            'catalog_number': catalog_number,
            'title': title,
            'description': description
        })
        
        query = """
        INSERT INTO course_catalog (subject, catalog_number, title, description, min_credits, max_credits, attributes, source_hash)
        VALUES (:subject, :catalog_number, :title, :description, :min_credits, :max_credits, :attributes, :source_hash)
        ON CONFLICT (subject, catalog_number, COALESCE(effective_start, '1900-01-01'::date)) DO UPDATE SET
            title = EXCLUDED.title,
            description = EXCLUDED.description,
            min_credits = EXCLUDED.min_credits,
            max_credits = EXCLUDED.max_credits,
            attributes = EXCLUDED.attributes,
            source_hash = EXCLUDED.source_hash,
            updated_at = NOW()
        RETURNING id
        """
        
        params = {
            'subject': subject,
            'catalog_number': catalog_number,
            'title': title,
            'description': description,
            'min_credits': min_credits,
            'max_credits': max_credits,
            'attributes': json.dumps(attributes) if attributes else None,
            'source_hash': source_hash
        }
        
        result = self.execute_query(query, params, fetch=True)
        return result[0]['id']

    def upsert_course_offering(self, term_id: int, catalog_id: int, topic: str = None, 
                              grading_basis: str = 'Graded') -> int:
        """Insert or update a course offering and return its ID"""
        source_hash = self.create_hash({
            'term_id': term_id,
            'catalog_id': catalog_id,
            'topic': topic,
            'grading_basis': grading_basis
        })
        
        # Since we don't have sis_offering_id, use term_id + catalog_id for uniqueness
        query = """
        WITH existing AS (
            SELECT id FROM course_offerings 
            WHERE term_id = :term_id AND catalog_id = :catalog_id
            LIMIT 1
        ),
        inserted AS (
            INSERT INTO course_offerings (term_id, catalog_id, topic, grading_basis, source_hash)
            SELECT :term_id, :catalog_id, :topic, :grading_basis, :source_hash
            WHERE NOT EXISTS (SELECT 1 FROM existing)
            RETURNING id
        ),
        updated AS (
            UPDATE course_offerings SET
                topic = :topic,
                grading_basis = :grading_basis,
                source_hash = :source_hash,
                updated_at = NOW()
            WHERE term_id = :term_id AND catalog_id = :catalog_id
            AND EXISTS (SELECT 1 FROM existing)
            RETURNING id
        )
        SELECT id FROM inserted UNION ALL SELECT id FROM updated UNION ALL SELECT id FROM existing
        """
        
        params = {
            'term_id': term_id,
            'catalog_id': catalog_id,
            'topic': topic,
            'grading_basis': grading_basis,
            'source_hash': source_hash
        }
        
        result = self.execute_query(query, params, fetch=True)
        return result[0]['id']

    def upsert_section(self, offering_id: int, component: str, section_number: str,
                      class_nbr: str = None, total_seats: int = None, 
                      waitlist_capacity: int = None, status: str = 'Open') -> int:
        """Insert or update a section and return its ID"""
        source_hash = self.create_hash({
            'offering_id': offering_id,
            'component': component,
            'section_number': section_number,
            'class_nbr': class_nbr
        })
        
        query = """
        INSERT INTO sections (offering_id, component, section_number, class_nbr, total_seats, waitlist_capacity, status, source_hash)
        VALUES (:offering_id, :component, :section_number, :class_nbr, :total_seats, :waitlist_capacity, :status, :source_hash)
        ON CONFLICT (offering_id, section_number) DO UPDATE SET
            component = EXCLUDED.component,
            class_nbr = EXCLUDED.class_nbr,
            total_seats = EXCLUDED.total_seats,
            waitlist_capacity = EXCLUDED.waitlist_capacity,
            status = EXCLUDED.status,
            source_hash = EXCLUDED.source_hash,
            updated_at = NOW()
        RETURNING id
        """
        
        params = {
            'offering_id': offering_id,
            'component': component,
            'section_number': section_number,
            'class_nbr': class_nbr,
            'total_seats': total_seats,
            'waitlist_capacity': waitlist_capacity,
            'status': status,
            'source_hash': source_hash
        }
        
        result = self.execute_query(query, params, fetch=True)
        return result[0]['id']

    def insert_meeting_pattern(self, section_id: int, day_mask: str = None, 
                              start_time: str = None, end_time: str = None,
                              start_date: str = None, end_date: str = None, 
                              location: str = None):
        """Insert a meeting pattern for a section"""
        query = """
        INSERT INTO meeting_patterns (section_id, day_mask, start_time, end_time, start_date, end_date, location)
        VALUES (:section_id, :day_mask, :start_time, :end_time, :start_date, :end_date, :location)
        """
        
        params = {
            'section_id': section_id,
            'day_mask': day_mask,
            'start_time': start_time,
            'end_time': end_time,
            'start_date': start_date,
            'end_date': end_date,
            'location': location
        }
        
        self.execute_query(query, params)

    def insert_section_snapshot(self, section_id: int, seats_avail: int = None, 
                               waitlist_avail: int = None, captured_at: datetime = None):
        """Insert a section enrollment snapshot"""
        if not captured_at:
            captured_at = datetime.now()
            
        query = """
        INSERT INTO section_snapshots (section_id, captured_at, seats_avail, waitlist_avail)
        VALUES (:section_id, :captured_at, :seats_avail, :waitlist_avail)
        ON CONFLICT (section_id, captured_at) DO UPDATE SET
            seats_avail = EXCLUDED.seats_avail,
            waitlist_avail = EXCLUDED.waitlist_avail
        """
        
        params = {
            'section_id': section_id,
            'captured_at': captured_at,
            'seats_avail': seats_avail,
            'waitlist_avail': waitlist_avail
        }
        
        self.execute_query(query, params)

    def get_or_create_catalog_id(self, subject: str, catalog_number: str) -> Optional[int]:
        """Get existing catalog ID or return None if not found"""
        query = """
        SELECT id FROM course_catalog 
        WHERE subject = :subject AND catalog_number = :catalog_number 
        AND (effective_end IS NULL OR effective_end > NOW())
        ORDER BY effective_start DESC NULLS LAST
        LIMIT 1
        """
        
        params = {
            'subject': subject,
            'catalog_number': catalog_number
        }
        
        result = self.execute_query(query, params, fetch=True)
        return result[0]['id'] if result else None

    def parse_day_mask(self, days_str: str) -> str:
        """Convert UVA day format to day mask"""
        if not days_str or days_str == '-':
            return None
            
        day_mapping = {
            'Mo': 'M',
            'Tu': 'T', 
            'We': 'W',
            'Th': 'R',
            'Fr': 'F',
            'Sa': 'S',
            'Su': 'U'
        }
        
        result = ''
        for day_abbr, mask_char in day_mapping.items():
            if day_abbr in days_str:
                result += mask_char
                
        return result if result else None

    def parse_semester_code(self, strm: str) -> tuple:
        """Parse semester code to readable format"""
        if len(strm) != 4:
            return strm, strm
            
        century = '20' if strm[0] == '1' else '19'
        year = century + strm[1:3]
        
        semester_map = {
            '2': ('Spring', f'SP{year}'),
            '6': ('Summer', f'SU{year}'),
            '8': ('Fall', f'FA{year}')
        }
        
        semester_info = semester_map.get(strm[3], ('Unknown', strm))
        return f"{semester_info[0]} {year}", semester_info[1]

    def test_connection(self) -> bool:
        """Test database connection"""
        try:
            with self.get_connection() as conn:
                result = conn.execute(text("SELECT 1"))
                return True
        except Exception as e:
            print(f"Connection test failed: {e}")
            return False

    def close(self):
        """Close the Cloud SQL connector"""
        if hasattr(self, 'connector'):
            self.connector.close()

    def get_pool_status(self) -> Dict[str, Any]:
        """Get connection pool status for monitoring"""
        return {
            'engine_url': str(self.engine.url),
            'pool_class': str(type(self.engine.pool)),
            'connection_name': self.connection_name
        }