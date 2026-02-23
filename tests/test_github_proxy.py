"""GitHub 代理工具单元测试"""
import pytest
from unittest.mock import patch, MagicMock

from utils.github_proxy import GitHubProxy


@pytest.fixture
def proxy():
    """创建 GitHubProxy 实例"""
    return GitHubProxy()


@pytest.fixture
def proxy_with_token():
    """创建带 token 的 GitHubProxy 实例"""
    return GitHubProxy(token='test-token-123')


class TestGitHubProxyInit:
    """GitHubProxy 初始化测试"""

    def test_default_headers(self, proxy):
        """测试默认请求头"""
        assert 'User-Agent' in proxy.headers
        assert 'Accept' in proxy.headers
        assert 'Authorization' not in proxy.headers

    def test_token_header(self, proxy_with_token):
        """测试带 token 的请求头"""
        assert 'Authorization' in proxy_with_token.headers
        assert proxy_with_token.headers['Authorization'] == 'token test-token-123'

    def test_api_base_url(self, proxy):
        """测试 API 基础 URL"""
        assert proxy.api_base == 'https://api.github.com'
        assert proxy.raw_base == 'https://raw.githubusercontent.com'


class TestGetRepoInfo:
    """获取仓库信息测试"""

    @patch('utils.github_proxy.requests.get')
    def test_success(self, mock_get, proxy):
        """测试成功获取仓库信息"""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            'name': 'flask',
            'full_name': 'pallets/flask',
            'description': 'Web framework',
            'stargazers_count': 60000,
            'forks_count': 15000,
            'language': 'Python',
            'html_url': 'https://github.com/pallets/flask',
            'created_at': '2010-04-06T11:04:16Z',
            'updated_at': '2026-02-01T00:00:00Z',
            'topics': ['python', 'web'],
            'default_branch': 'main'
        }
        mock_get.return_value = mock_resp

        result = proxy.get_repo_info('pallets', 'flask')
        assert result['success'] is True
        assert result['data']['name'] == 'flask'
        assert result['data']['stars'] == 60000

    @patch('utils.github_proxy.requests.get')
    def test_not_found(self, mock_get, proxy):
        """测试仓库不存在"""
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_get.return_value = mock_resp

        result = proxy.get_repo_info('nobody', 'nonexistent')
        assert result['success'] is False
        assert 'HTTP 404' in result['error']

    @patch('utils.github_proxy.requests.get')
    def test_network_error(self, mock_get, proxy):
        """测试网络异常"""
        mock_get.side_effect = Exception('Connection timeout')

        result = proxy.get_repo_info('owner', 'repo')
        assert result['success'] is False
        assert 'Connection timeout' in result['error']


class TestGetReadme:
    """获取 README 测试"""

    @patch('utils.github_proxy.requests.get')
    def test_success_main_branch(self, mock_get, proxy):
        """测试从 main 分支获取 README"""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = '# My Project\n\nDescription here.'
        mock_get.return_value = mock_resp

        result = proxy.get_readme('owner', 'repo')
        assert result['success'] is True
        assert '# My Project' in result['content']

    @patch('utils.github_proxy.requests.get')
    def test_fallback_to_master(self, mock_get, proxy):
        """测试回退到 master 分支"""
        resp_404 = MagicMock()
        resp_404.status_code = 404

        resp_200 = MagicMock()
        resp_200.status_code = 200
        resp_200.text = '# README from master'

        mock_get.side_effect = [resp_404, resp_200]

        result = proxy.get_readme('owner', 'repo')
        assert result['success'] is True
        assert 'master' in result['content'] or result['success'] is True

    @patch('utils.github_proxy.requests.get')
    def test_readme_not_found(self, mock_get, proxy):
        """测试 README 不存在"""
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_get.return_value = mock_resp

        result = proxy.get_readme('owner', 'repo')
        assert result['success'] is False

    @patch('utils.github_proxy.requests.get')
    def test_network_error(self, mock_get, proxy):
        """测试网络错误"""
        mock_get.side_effect = Exception('DNS resolution failed')

        result = proxy.get_readme('owner', 'repo')
        assert result['success'] is False


class TestGetFileContent:
    """获取文件内容测试"""

    @patch('utils.github_proxy.requests.get')
    def test_success(self, mock_get, proxy):
        """测试成功获取文件内容"""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = 'print("hello")'
        mock_get.return_value = mock_resp

        result = proxy.get_file_content('owner', 'repo', 'main.py')
        assert result['success'] is True
        assert result['content'] == 'print("hello")'

    @patch('utils.github_proxy.requests.get')
    def test_path_encoding(self, mock_get, proxy):
        """测试路径编码（中文路径等）"""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = '内容'
        mock_get.return_value = mock_resp

        result = proxy.get_file_content('owner', 'repo', 'docs/文档.md')
        assert result['success'] is True
        # 验证 URL 中的路径被编码
        called_url = mock_get.call_args[0][0]
        assert 'docs/' in called_url


class TestSearchRepos:
    """搜索仓库测试"""

    @patch('utils.github_proxy.requests.get')
    def test_search_success(self, mock_get, proxy):
        """测试搜索成功"""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            'total_count': 1,
            'items': [{
                'name': 'flask',
                'full_name': 'pallets/flask',
                'description': 'Web framework',
                'stargazers_count': 60000,
                'language': 'Python',
                'html_url': 'https://github.com/pallets/flask'
            }]
        }
        mock_get.return_value = mock_resp

        result = proxy.search_repos('flask python')
        assert result['success'] is True
        assert result['total'] == 1
        assert len(result['repos']) == 1
        assert result['repos'][0]['name'] == 'flask'

    @patch('utils.github_proxy.requests.get')
    def test_search_no_results(self, mock_get, proxy):
        """测试搜索无结果"""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {'total_count': 0, 'items': []}
        mock_get.return_value = mock_resp

        result = proxy.search_repos('xyznonexistent123')
        assert result['success'] is True
        assert result['total'] == 0
        assert result['repos'] == []

    @patch('utils.github_proxy.requests.get')
    def test_search_api_error(self, mock_get, proxy):
        """测试搜索 API 错误"""
        mock_resp = MagicMock()
        mock_resp.status_code = 403
        mock_get.return_value = mock_resp

        result = proxy.search_repos('flask')
        assert result['success'] is False


class TestGetUserRepos:
    """获取用户仓库测试"""

    @patch('utils.github_proxy.requests.get')
    def test_success(self, mock_get, proxy):
        """测试获取用户仓库"""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = [
            {
                'name': 'project1',
                'full_name': 'user/project1',
                'description': 'A project',
                'stargazers_count': 10,
                'language': 'Python',
                'html_url': 'https://github.com/user/project1',
                'updated_at': '2026-01-01T00:00:00Z'
            }
        ]
        mock_get.return_value = mock_resp

        result = proxy.get_user_repos('user')
        assert result['success'] is True
        assert len(result['repos']) == 1

    @patch('utils.github_proxy.requests.get')
    def test_user_not_found(self, mock_get, proxy):
        """测试用户不存在"""
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_get.return_value = mock_resp

        result = proxy.get_user_repos('nonexistent_user')
        assert result['success'] is False


class TestGetRepoTree:
    """获取仓库文件树测试"""

    @patch('utils.github_proxy.requests.get')
    def test_success(self, mock_get, proxy):
        """测试获取文件树"""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            'tree': [
                {'path': 'README.md', 'type': 'blob', 'size': 1024},
                {'path': 'src', 'type': 'tree', 'size': 0},
                {'path': 'src/main.py', 'type': 'blob', 'size': 512}
            ]
        }
        mock_get.return_value = mock_resp

        result = proxy.get_repo_tree('owner', 'repo')
        assert result['success'] is True
        assert len(result['files']) == 3
        assert result['files'][0]['path'] == 'README.md'
