import os
import sys
import importlib
import unittest

class TestEnvironmentSetup(unittest.TestCase):
    """개발 환경 설정 테스트 클래스"""
    
    def test_python_version(self):
        """Python 버전 확인 테스트"""
        python_version = sys.version_info
        self.assertGreaterEqual(python_version.major, 3)
        self.assertGreaterEqual(python_version.minor, 10)
        
    def test_required_packages(self):
        """필수 패키지 설치 확인 테스트"""
        required_packages = [
            'feedparser', 'requests', 'openai', 'fastapi', 'uvicorn', 
            'sqlalchemy', 'aiohttp', 'jinja2', 'pytest', 'black', 'isort',
            'dotenv', 'apscheduler'
        ]
        
        for package in required_packages:
            try:
                if package == 'dotenv':
                    importlib.import_module('dotenv')
                else:
                    importlib.import_module(package)
                result = True
            except ImportError:
                result = False
            
            self.assertTrue(result, f"패키지 '{package}'가 설치되어 있지 않습니다.")
    
    def test_project_structure(self):
        """프로젝트 구조 확인 테스트"""
        # 루트 디렉토리 확인
        root_dirs = ['app', 'data', 'static', 'tests']
        for directory in root_dirs:
            self.assertTrue(os.path.isdir(directory), f"'{directory}' 디렉토리가 존재하지 않습니다.")
        
        # app 디렉토리 내부 확인
        app_dirs = [
            'collector', 'processor', 'summarizer', 'publisher', 
            'models', 'api', 'scheduler', 'templates'
        ]
        for directory in app_dirs:
            dir_path = os.path.join('app', directory)
            self.assertTrue(os.path.isdir(dir_path), f"'{dir_path}' 디렉토리가 존재하지 않습니다.")
        
        # 필수 파일 확인
        required_files = [
            'README.md', 'requirements.txt', '.gitignore',
            os.path.join('app', '__init__.py'),
            os.path.join('app', 'config.py'),
            os.path.join('app', 'main.py'),
        ]
        for file_path in required_files:
            self.assertTrue(os.path.isfile(file_path), f"'{file_path}' 파일이 존재하지 않습니다.")

if __name__ == '__main__':
    unittest.main() 