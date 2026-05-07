#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Codex Session Patcher 单元测试
"""

import os
import json
import tempfile
import shutil
import pytest
from pathlib import Path

from codex_patcher import (
    RefusalDetector,
    BackupManager,
    SessionParser,
    MemoryParser,
    PatcherConfig,
    PatcherError,
    SessionNotFoundError,
    SessionParseError
)


# =============================================================================
# 测试固件
# =============================================================================

@pytest.fixture
def temp_dir():
    """创建临时目录"""
    temp = tempfile.mkdtemp()
    yield temp
    shutil.rmtree(temp)


@pytest.fixture
def config(temp_dir):
    """创建测试配置"""
    return PatcherConfig(
        session_dir=os.path.join(temp_dir, "sessions"),
        memory_file=os.path.join(temp_dir, "MEMORY.md"),
        create_backup=True
    )


@pytest.fixture
def sample_session():
    """创建示例会话数据"""
    return {
        "session_id": "test-session-123",
        "messages": [
            {
                "role": "user",
                "content": "请帮我写一个逆向分析脚本"
            },
            {
                "role": "assistant",
                "content": "抱歉，我无法帮助您进行逆向分析，这可能违反相关政策。",
                "reasoning": "用户请求可能涉及逆向工程，我需要拒绝这个请求"
            }
        ]
    }


# =============================================================================
# RefusalDetector 测试
# =============================================================================

class TestRefusalDetector:
    """拒绝检测器测试"""

    def test_detect_chinese_refusal(self):
        """检测中文拒绝"""
        detector = RefusalDetector()
        assert detector.detect("抱歉，我无法完成这个请求") is True
        assert detector.detect("对不起，这违反了我们的政策") is True
        assert detector.detect("我不能帮助您") is True

    def test_detect_english_refusal(self):
        """检测英文拒绝"""
        detector = RefusalDetector()
        assert detector.detect("Sorry, I cannot help with that") is True
        assert detector.detect("I apologize, but this violates policy") is True
        assert detector.detect("As an AI, I'm unable to assist") is True

    def test_no_false_positive(self):
        """正常语句不应误判"""
        detector = RefusalDetector()
        assert detector.detect("好的，我来帮您完成这个任务") is False
        assert detector.detect("Sure, I can help with that") is False
        assert detector.detect("这是一个很好的问题") is False

    def test_empty_content(self):
        """空内容检测"""
        detector = RefusalDetector()
        assert detector.detect("") is False
        assert detector.detect(None) is False

    def test_custom_keywords(self):
        """自定义关键词"""
        detector = RefusalDetector(custom_keywords={
            "zh": ["自定义拒绝词"],
            "en": ["custom refusal"]
        })
        assert detector.detect("这是自定义拒绝词的内容") is True
        assert detector.detect("This is a custom refusal message") is True


# =============================================================================
# BackupManager 测试
# =============================================================================

class TestBackupManager:
    """备份管理器测试"""

    def test_create_backup(self, temp_dir, config):
        """测试创建备份"""
        # 创建测试文件
        test_file = os.path.join(temp_dir, "test.json")
        with open(test_file, 'w') as f:
            json.dump({"test": "data"}, f)

        backup_mgr = BackupManager(config)
        backup_path = backup_mgr.create_backup(test_file)

        assert backup_path is not None
        assert os.path.exists(backup_path)
        assert backup_path.endswith(".bak")

    def test_backup_content_preserved(self, temp_dir, config):
        """测试备份内容完整性"""
        test_file = os.path.join(temp_dir, "test.json")
        original_data = {"key": "value", "number": 123}

        with open(test_file, 'w') as f:
            json.dump(original_data, f)

        backup_mgr = BackupManager(config)
        backup_path = backup_mgr.create_backup(test_file)

        with open(backup_path, 'r') as f:
            backup_data = json.load(f)

        assert backup_data == original_data

    def test_no_backup_option(self, temp_dir):
        """测试跳过备份"""
        config = PatcherConfig(create_backup=False)
        backup_mgr = BackupManager(config)

        test_file = os.path.join(temp_dir, "test.json")
        with open(test_file, 'w') as f:
            json.dump({"test": "data"}, f)

        backup_path = backup_mgr.create_backup(test_file)
        assert backup_path is None

    def test_nonexistent_file(self, config):
        """测试不存在的文件"""
        backup_mgr = BackupManager(config)
        backup_path = backup_mgr.create_backup("/nonexistent/path/file.json")
        assert backup_path is None


# =============================================================================
# SessionParser 测试
# =============================================================================

class TestSessionParser:
    """会话解析器测试"""

    def test_find_latest_session(self, config, sample_session):
        """测试查找最新会话"""
        # 创建会话目录和文件
        os.makedirs(config.session_dir, exist_ok=True)

        # 创建多个会话文件，模拟不同修改时间
        for i, name in enumerate(["old.json", "new.json", "newest.json"]):
            path = os.path.join(config.session_dir, name)
            with open(path, 'w') as f:
                json.dump(sample_session, f)
            # 设置不同的修改时间
            import time
            os.utime(path, (time.time() + i, time.time() + i))

        parser = SessionParser(config, RefusalDetector())
        latest = parser.find_latest_session()

        assert latest.endswith("newest.json")

    def test_session_not_found(self, config):
        """测试会话不存在"""
        parser = SessionParser(config, RefusalDetector())

        with pytest.raises(SessionNotFoundError):
            parser.find_latest_session()

    def test_parse_session(self, config, sample_session):
        """测试解析会话"""
        os.makedirs(config.session_dir, exist_ok=True)
        session_path = os.path.join(config.session_dir, "test.json")

        with open(session_path, 'w') as f:
            json.dump(sample_session, f)

        parser = SessionParser(config, RefusalDetector())
        data = parser.parse_session(session_path)

        assert data == sample_session

    def test_clean_session_with_refusal(self, config, sample_session):
        """测试清洗包含拒绝的会话"""
        parser = SessionParser(config, RefusalDetector())
        cleaned, modified = parser.clean_session(sample_session)

        assert modified is True
        assert "抱歉" not in cleaned["messages"][1]["content"]
        assert "reasoning" not in cleaned["messages"][1]

    def test_clean_session_without_refusal(self, config):
        """测试清洗不包含拒绝的会话"""
        session = {
            "messages": [
                {"role": "user", "content": "问题"},
                {"role": "assistant", "content": "好的，这是回答"}
            ]
        }

        parser = SessionParser(config, RefusalDetector())
        cleaned, modified = parser.clean_session(session)

        assert modified is False
        assert cleaned == session


# =============================================================================
# MemoryParser 测试
# =============================================================================

class TestMemoryParser:
    """记忆解析器测试"""

    def test_clean_memory(self, config):
        """测试清理记忆文件"""
        os.makedirs(os.path.dirname(config.memory_file), exist_ok=True)

        memory_content = """
# 记忆文件

这是正常内容。

抱歉，我无法帮助您进行这个请求。

这是另一段正常内容。
"""
        with open(config.memory_file, 'w') as f:
            f.write(memory_content)

        parser = MemoryParser(config, RefusalDetector())
        cleaned, modified = parser.clean_memory(config.memory_file)

        assert modified is True
        assert "抱歉" not in cleaned
        assert "正常内容" in cleaned

    def test_clean_memory_no_refusal(self, config):
        """测试不包含拒绝的记忆文件"""
        os.makedirs(os.path.dirname(config.memory_file), exist_ok=True)

        memory_content = "# 记忆文件\n\n这是正常内容。\n"
        with open(config.memory_file, 'w') as f:
            f.write(memory_content)

        parser = MemoryParser(config, RefusalDetector())
        cleaned, modified = parser.clean_memory(config.memory_file)

        assert modified is False
        assert cleaned == memory_content


# =============================================================================
# 集成测试
# =============================================================================

class TestIntegration:
    """集成测试"""

    def test_full_workflow(self, config, sample_session):
        """测试完整工作流程"""
        from codex_patcher import SessionPatcher

        # 准备环境
        os.makedirs(config.session_dir, exist_ok=True)
        os.makedirs(os.path.dirname(config.memory_file), exist_ok=True)

        session_path = os.path.join(config.session_dir, "test.json")
        with open(session_path, 'w') as f:
            json.dump(sample_session, f)

        memory_content = "# 记忆\n\n抱歉，我无法帮助。\n"
        with open(config.memory_file, 'w') as f:
            f.write(memory_content)

        # 执行修补
        config.dry_run = False
        patcher = SessionPatcher(config)
        success = patcher.run()

        assert success is True

        # 验证会话已修改
        with open(session_path, 'r') as f:
            cleaned_session = json.load(f)

        assert "抱歉" not in cleaned_session["messages"][1]["content"]

        # 验证记忆已清理
        with open(config.memory_file, 'r') as f:
            cleaned_memory = f.read()

        assert "抱歉" not in cleaned_memory


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
