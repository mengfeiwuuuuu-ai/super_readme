"""GitHub 代理工具 - 用于代理 GitHub 内容展示"""
import requests
from urllib.parse import quote


class GitHubProxy:
    """GitHub 内容代理，支持获取仓库信息、文件内容、README 等"""

    def __init__(self, token=None):
        self.api_base = 'https://api.github.com'
        self.raw_base = 'https://raw.githubusercontent.com'
        self.headers = {
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'MyBlob-Blog-System'
        }
        if token:
            self.headers['Authorization'] = f'token {token}'

    def get_repo_info(self, owner, repo):
        """获取仓库基本信息"""
        url = f'{self.api_base}/repos/{owner}/{repo}'
        try:
            resp = requests.get(url, headers=self.headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                return {
                    'success': True,
                    'data': {
                        'name': data.get('name'),
                        'full_name': data.get('full_name'),
                        'description': data.get('description'),
                        'stars': data.get('stargazers_count'),
                        'forks': data.get('forks_count'),
                        'language': data.get('language'),
                        'html_url': data.get('html_url'),
                        'created_at': data.get('created_at'),
                        'updated_at': data.get('updated_at'),
                        'topics': data.get('topics', []),
                        'default_branch': data.get('default_branch', 'main')
                    }
                }
            return {'success': False, 'error': f'HTTP {resp.status_code}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def get_readme(self, owner, repo, branch='main'):
        """获取仓库 README 内容"""
        url = f'{self.raw_base}/{owner}/{repo}/{branch}/README.md'
        try:
            resp = requests.get(url, headers={'User-Agent': 'MyBlob-Blog-System'}, timeout=10)
            if resp.status_code == 200:
                return {'success': True, 'content': resp.text}
            # 尝试 master 分支
            url = f'{self.raw_base}/{owner}/{repo}/master/README.md'
            resp = requests.get(url, headers={'User-Agent': 'MyBlob-Blog-System'}, timeout=10)
            if resp.status_code == 200:
                return {'success': True, 'content': resp.text}
            return {'success': False, 'error': 'README not found'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def get_file_content(self, owner, repo, path, branch='main'):
        """获取仓库中某个文件的内容"""
        encoded_path = quote(path, safe='/')
        url = f'{self.raw_base}/{owner}/{repo}/{branch}/{encoded_path}'
        try:
            resp = requests.get(url, headers={'User-Agent': 'MyBlob-Blog-System'}, timeout=10)
            if resp.status_code == 200:
                return {'success': True, 'content': resp.text}
            return {'success': False, 'error': f'HTTP {resp.status_code}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def get_repo_tree(self, owner, repo, branch='main'):
        """获取仓库文件树"""
        url = f'{self.api_base}/repos/{owner}/{repo}/git/trees/{branch}?recursive=1'
        try:
            resp = requests.get(url, headers=self.headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                files = []
                for item in data.get('tree', []):
                    files.append({
                        'path': item.get('path'),
                        'type': item.get('type'),
                        'size': item.get('size', 0)
                    })
                return {'success': True, 'files': files}
            return {'success': False, 'error': f'HTTP {resp.status_code}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def search_repos(self, query, sort='stars', per_page=10):
        """搜索 GitHub 仓库"""
        url = f'{self.api_base}/search/repositories'
        params = {'q': query, 'sort': sort, 'per_page': per_page}
        try:
            resp = requests.get(url, headers=self.headers, params=params, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                repos = []
                for item in data.get('items', []):
                    repos.append({
                        'name': item.get('name'),
                        'full_name': item.get('full_name'),
                        'description': item.get('description'),
                        'stars': item.get('stargazers_count'),
                        'language': item.get('language'),
                        'html_url': item.get('html_url')
                    })
                return {'success': True, 'repos': repos, 'total': data.get('total_count', 0)}
            return {'success': False, 'error': f'HTTP {resp.status_code}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def get_user_repos(self, username, per_page=30):
        """获取用户的公开仓库列表"""
        url = f'{self.api_base}/users/{username}/repos'
        params = {'per_page': per_page, 'sort': 'updated'}
        try:
            resp = requests.get(url, headers=self.headers, params=params, timeout=10)
            if resp.status_code == 200:
                repos = []
                for item in resp.json():
                    repos.append({
                        'name': item.get('name'),
                        'full_name': item.get('full_name'),
                        'description': item.get('description'),
                        'stars': item.get('stargazers_count'),
                        'language': item.get('language'),
                        'html_url': item.get('html_url'),
                        'updated_at': item.get('updated_at')
                    })
                return {'success': True, 'repos': repos}
            return {'success': False, 'error': f'HTTP {resp.status_code}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
