"""
示例测试 - 验证测试框架正常工作
"""

import pytest
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'fund_search'))


class TestExample:
    """示例测试类"""
    
    def test_basic_assertion(self):
        """测试基本断言"""
        assert 1 + 1 == 2
        assert "hello".upper() == "HELLO"
    
    def test_list_operations(self):
        """测试列表操作"""
        my_list = [1, 2, 3]
        assert len(my_list) == 3
        assert 2 in my_list
        my_list.append(4)
        assert len(my_list) == 4
    
    def test_dictionary_operations(self):
        """测试字典操作"""
        my_dict = {'name': '测试', 'value': 100}
        assert my_dict['name'] == '测试'
        assert 'value' in my_dict
        my_dict['new_key'] = 'new_value'
        assert my_dict['new_key'] == 'new_value'
    
    @pytest.mark.parametrize("input,expected", [
        (1, 1),
        (2, 4),
        (3, 9),
        (4, 16),
    ])
    def test_square(self, input, expected):
        """参数化测试示例"""
        assert input ** 2 == expected
    
    def test_exception_handling(self):
        """测试异常处理"""
        with pytest.raises(ZeroDivisionError):
            1 / 0
        
        with pytest.raises(KeyError):
            my_dict = {}
            _ = my_dict['nonexistent_key']


class TestProjectStructure:
    """测试项目结构"""
    
    def test_project_directories_exist(self):
        """测试项目目录是否存在"""
        project_root = os.path.join(os.path.dirname(__file__), '..', '..')
        
        required_dirs = [
            'fund_search',
            'fund_search/web',
            'fund_search/data_retrieval',
            'fund_search/backtesting',
            'tests',
            'tests/unit',
            'tests/integration',
        ]
        
        for dir_name in required_dirs:
            dir_path = os.path.join(project_root, dir_name)
            assert os.path.exists(dir_path), f"目录不存在: {dir_name}"
    
    def test_required_files_exist(self):
        """测试必要文件是否存在"""
        project_root = os.path.join(os.path.dirname(__file__), '..', '..')
        
        required_files = [
            'requirements.txt',
<<<<<<< HEAD
            'fund_search/web/app_enhanced.py',
            'pytest.ini',
=======
            'fund_search/web/app.py',
            'pytest.ini',
            'Makefile',
>>>>>>> e7314991467ef81fa7ebe96d0b2fafdd7a30d714
        ]
        
        for file_name in required_files:
            file_path = os.path.join(project_root, file_name)
            assert os.path.exists(file_path), f"文件不存在: {file_name}"


class TestCI_CDComponents:
    """测试CI/CD组件"""
    
    def test_ci_cd_scripts_exist(self):
        """测试CI/CD脚本是否存在"""
        ci_cd_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'ci-cd')
        
        scripts = [
            'local-ci.ps1',
            'deploy.ps1',
            'run-tests.ps1',
        ]
        
        for script in scripts:
            script_path = os.path.join(ci_cd_dir, script)
            assert os.path.exists(script_path), f"CI/CD脚本不存在: {script}"
    
    def test_github_workflows_exist(self):
        """测试GitHub工作流配置是否存在"""
        workflows_dir = os.path.join(
            os.path.dirname(__file__), '..', '..', 
            '.github', 'workflows'
        )
        
        if os.path.exists(workflows_dir):
            workflow_files = os.listdir(workflows_dir)
            assert len(workflow_files) > 0, "没有找到工作流文件"
    
    def test_pytest_config_exists(self):
        """测试pytest配置是否存在"""
        config_file = os.path.join(
            os.path.dirname(__file__), '..', '..', 
            'pytest.ini'
        )
        assert os.path.exists(config_file), "pytest.ini 不存在"


class TestMockExamples:
    """Mock测试示例"""
    
    def test_mock_function_call(self, mocker):
        """测试Mock函数调用"""
        # 创建一个Mock对象
        mock_func = mocker.MagicMock(return_value=42)
        
        # 调用Mock函数
        result = mock_func()
        
        # 验证结果
        assert result == 42
        mock_func.assert_called_once()
    
    def test_mock_with_side_effect(self, mocker):
        """测试带副作用的Mock"""
        mock_func = mocker.MagicMock()
        mock_func.side_effect = [1, 2, 3]
        
        assert mock_func() == 1
        assert mock_func() == 2
        assert mock_func() == 3
    
    def test_mock_exception(self, mocker):
        """测试Mock异常"""
        mock_func = mocker.MagicMock()
        mock_func.side_effect = ValueError("测试错误")
        
        with pytest.raises(ValueError, match="测试错误"):
            mock_func()


# 标记为慢速测试的示例
@pytest.mark.slow
def test_slow_operation():
    """慢速测试示例"""
    import time
    time.sleep(0.1)  # 模拟慢速操作
    assert True


# 标记为跳过的测试示例
@pytest.mark.skip(reason="示例：此测试被跳过")
def test_skipped_example():
    """被跳过的测试示例"""
    assert False  # 这不会被执行


# 条件跳过示例
@pytest.mark.skipif(
    sys.platform == "win32",
    reason="示例：在Windows上跳过"
)
def test_unix_only_feature():
    """仅在Unix系统上运行的测试"""
    assert True
