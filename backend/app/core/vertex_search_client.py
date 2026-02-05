"""
GAIM Lab - Vertex AI Search 클라이언트
Google Cloud Discovery Engine API를 활용한 대규모 문서 검색
"""

import os
import sys
import io
from typing import List, Dict, Optional
from pathlib import Path

# Windows 콘솔 UTF-8 출력 설정
if sys.stdout and hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Vertex AI Search 의존성 체크
try:
    from google.cloud import discoveryengine_v1 as discoveryengine
    from google.api_core.client_options import ClientOptions
    HAS_VERTEX_SEARCH = True
except ImportError:
    HAS_VERTEX_SEARCH = False
    discoveryengine = None

# 환경 변수
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "gaim-lab-project-2024")
LOCATION = os.getenv("VERTEX_LOCATION", "global")


class VertexSearchClient:
    """
    Vertex AI Search 클라이언트
    
    Google Cloud Discovery Engine을 활용한 고성능 문서 검색 시스템.
    인메모리 RAG보다 대규모 문서 처리에 적합.
    """
    
    def __init__(
        self,
        project_id: str = None,
        location: str = None,
        datastore_id: str = None,
        engine_id: str = None
    ):
        """
        Vertex AI Search 클라이언트 초기화
        
        Args:
            project_id: GCP 프로젝트 ID
            location: 데이터 스토어 위치 (global 권장)
            datastore_id: 데이터 스토어 ID (문서 저장소)
            engine_id: 검색 엔진 ID
        """
        self.project_id = project_id or PROJECT_ID
        self.location = location or LOCATION
        self.datastore_id = datastore_id or "gaim-education-docs"
        self.engine_id = engine_id or "gaim-search-engine"
        
        self.is_initialized = False
        self.search_client = None
        self.document_client = None
        
        if not HAS_VERTEX_SEARCH:
            print("⚠️ google-cloud-discoveryengine 패키지가 설치되지 않았습니다.")
            print("   pip install google-cloud-discoveryengine")
            return
        
        try:
            self._initialize_clients()
        except Exception as e:
            print(f"⚠️ Vertex AI Search 초기화 실패: {e}")
    
    def _initialize_clients(self):
        """클라이언트 초기화"""
        # API 엔드포인트 설정
        client_options = None
        if self.location != "global":
            client_options = ClientOptions(
                api_endpoint=f"{self.location}-discoveryengine.googleapis.com"
            )
        
        # 검색 클라이언트
        self.search_client = discoveryengine.SearchServiceClient(
            client_options=client_options
        )
        
        # 문서 클라이언트 (인덱싱용)
        self.document_client = discoveryengine.DocumentServiceClient(
            client_options=client_options
        )
        
        self.is_initialized = True
        print(f"✅ Vertex AI Search 초기화 완료")
        print(f"   프로젝트: {self.project_id}")
        print(f"   위치: {self.location}")
    
    @property
    def serving_config(self) -> str:
        """검색 서빙 설정 경로"""
        return (
            f"projects/{self.project_id}"
            f"/locations/{self.location}"
            f"/dataStores/{self.datastore_id}"
            f"/servingConfigs/default_search"
        )
    
    @property
    def datastore_path(self) -> str:
        """데이터 스토어 경로"""
        return (
            f"projects/{self.project_id}"
            f"/locations/{self.location}"
            f"/dataStores/{self.datastore_id}"
        )
    
    @property
    def branch_path(self) -> str:
        """문서 브랜치 경로"""
        return f"{self.datastore_path}/branches/default_branch"
    
    def search(
        self,
        query: str,
        k: int = 5,
        filter_expression: str = None
    ) -> List[Dict]:
        """
        문서 검색
        
        Args:
            query: 검색 쿼리
            k: 반환할 결과 수
            filter_expression: 필터 표현식 (선택)
            
        Returns:
            검색 결과 목록
        """
        if not self.is_initialized:
            print("❌ Vertex AI Search가 초기화되지 않았습니다.")
            return []
        
        try:
            # 검색 요청 생성
            request = discoveryengine.SearchRequest(
                serving_config=self.serving_config,
                query=query,
                page_size=k,
            )
            
            if filter_expression:
                request.filter = filter_expression
            
            # 검색 실행
            response = self.search_client.search(request)
            
            # 결과 파싱
            results = []
            for result in response.results:
                doc_data = result.document.derived_struct_data
                results.append({
                    "id": result.document.id,
                    "name": result.document.name,
                    "title": doc_data.get("title", ""),
                    "content": doc_data.get("content", ""),
                    "snippet": doc_data.get("snippet", ""),
                    "score": result.relevance_score if hasattr(result, 'relevance_score') else 0
                })
            
            return results
            
        except Exception as e:
            print(f"❌ 검색 오류: {e}")
            return []
    
    def index_document(
        self,
        doc_id: str,
        title: str,
        content: str,
        metadata: Dict = None
    ) -> bool:
        """
        단일 문서 인덱싱
        
        Args:
            doc_id: 문서 ID
            title: 문서 제목
            content: 문서 내용
            metadata: 추가 메타데이터
            
        Returns:
            성공 여부
        """
        if not self.is_initialized:
            print("❌ Vertex AI Search가 초기화되지 않았습니다.")
            return False
        
        try:
            # 문서 생성
            document = discoveryengine.Document(
                id=doc_id,
                struct_data={
                    "title": title,
                    "content": content,
                    **(metadata or {})
                }
            )
            
            # 문서 경로
            parent = self.branch_path
            
            # 문서 생성/업데이트
            request = discoveryengine.CreateDocumentRequest(
                parent=parent,
                document=document,
                document_id=doc_id
            )
            
            self.document_client.create_document(request)
            return True
            
        except Exception as e:
            print(f"❌ 문서 인덱싱 오류 ({doc_id}): {e}")
            return False
    
    def index_documents_from_directory(
        self,
        directory: str,
        file_extensions: List[str] = None
    ) -> int:
        """
        디렉토리의 모든 문서 인덱싱
        
        Args:
            directory: 문서 디렉토리 경로
            file_extensions: 파일 확장자 목록 (기본: .md, .txt)
            
        Returns:
            인덱싱된 문서 수
        """
        if file_extensions is None:
            file_extensions = [".md", ".txt"]
        
        directory_path = Path(directory)
        if not directory_path.exists():
            print(f"❌ 디렉토리를 찾을 수 없습니다: {directory}")
            return 0
        
        indexed_count = 0
        
        for ext in file_extensions:
            for file_path in directory_path.rglob(f"*{ext}"):
                try:
                    content = file_path.read_text(encoding="utf-8")
                    title = file_path.stem
                    doc_id = file_path.stem.replace(" ", "_").lower()
                    
                    # 메타데이터
                    metadata = {
                        "source": str(file_path),
                        "category": file_path.parent.name,
                        "file_type": ext
                    }
                    
                    if self.index_document(doc_id, title, content, metadata):
                        indexed_count += 1
                        print(f"   ✅ {file_path.name}")
                        
                except Exception as e:
                    print(f"   ❌ {file_path.name}: {e}")
        
        print(f"\n📚 총 {indexed_count}개 문서 인덱싱 완료")
        return indexed_count
    
    def delete_document(self, doc_id: str) -> bool:
        """문서 삭제"""
        if not self.is_initialized:
            return False
        
        try:
            name = f"{self.branch_path}/documents/{doc_id}"
            request = discoveryengine.DeleteDocumentRequest(name=name)
            self.document_client.delete_document(request)
            return True
        except Exception as e:
            print(f"❌ 문서 삭제 오류 ({doc_id}): {e}")
            return False


def get_vertex_search_client() -> Optional[VertexSearchClient]:
    """Vertex AI Search 클라이언트 싱글톤"""
    if not HAS_VERTEX_SEARCH:
        return None
    
    global _vertex_client
    if '_vertex_client' not in globals():
        _vertex_client = VertexSearchClient()
    return _vertex_client


# ============================================================
# 테스트
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("🔍 Vertex AI Search 클라이언트 테스트")
    print("=" * 60)
    
    # 환경 변수 로드
    from dotenv import load_dotenv
    load_dotenv("D:/AI/GAIM_Lab/.env")
    
    # 클라이언트 초기화
    client = VertexSearchClient()
    
    if client.is_initialized:
        print("\n✅ 클라이언트 초기화 성공!")
        print(f"   Serving Config: {client.serving_config}")
        
        # 검색 테스트 (데이터 스토어가 설정된 경우)
        # results = client.search("발문 전략", k=3)
        # for r in results:
        #     print(f"   - {r['title']}: {r['snippet'][:50]}...")
    else:
        print("\n⚠️ 클라이언트 초기화 실패")
        print("   1. google-cloud-discoveryengine 설치 확인")
        print("   2. GCP 인증 확인 (gcloud auth)")
        print("   3. Discovery Engine API 활성화 확인")
