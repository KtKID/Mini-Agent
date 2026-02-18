"""
Feishu Skill 自动化测试

测试消息收发、回复、读取、删除、表情反应等功能。
"""

import asyncio
import json
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mini_agent.skills.feishu_skill import FeishuSkill
from mini_agent.skills.feishu_skill.config import FeishuConfig


# 测试配置 - 优先从环境变量，否则从配置文件读取
APP_ID = os.getenv("FEISHU_APP_ID", "")
APP_SECRET = os.getenv("FEISHU_APP_SECRET", "")
TEST_OPEN_ID = os.getenv("FEISHU_TEST_OPEN_ID", "")  # 测试用户 open_id

# 如果环境变量未设置，尝试从配置文件读取
if not APP_ID or not APP_SECRET:
    try:
        import yaml
        from pathlib import Path

        config_path = Path("mini_agent/config/config.yaml")
        if config_path.exists():
            with open(config_path) as f:
                data = yaml.safe_load(f)
                feishu_config = data.get("feishu", {})
                if not APP_ID:
                    APP_ID = feishu_config.get("app_id", "")
                if not APP_SECRET:
                    APP_SECRET = feishu_config.get("app_secret", "")
    except Exception:
        pass


class TestResult:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []

    def add_pass(self, name):
        self.passed += 1
        print(f"  ✅ {name}")

    def add_fail(self, name, error):
        self.failed += 1
        self.errors.append((name, error))
        print(f"  ❌ {name}: {error}")

    def summary(self):
        print(f"\n{'='*50}")
        print(f"测试结果: {self.passed} 通过, {self.failed} 失败")
        print(f"{'='*50}")
        if self.errors:
            print("\n失败详情:")
            for name, error in self.errors:
                print(f"  - {name}: {error}")
        return self.failed == 0


async def test_config_validation(result: TestResult):
    """测试配置验证"""
    print("\n[测试 1] 配置验证")

    # 测试禁用配置 - disabled 配置视为"有效"(只是不启用)
    try:
        config = FeishuConfig(enabled=False)
        # disabled 配置 is_valid 应该返回 True (因为不需要验证凭证)
        if config.is_valid():
            result.add_pass("禁用配置验证")
        else:
            result.add_fail("禁用配置验证", "disabled 配置应该返回 True")
    except Exception as e:
        result.add_fail("禁用配置验证", str(e))

    # 测试有效配置
    try:
        config = FeishuConfig(
            enabled=True,
            app_id="cli_test123",
            app_secret="test_secret"
        )
        if config.is_valid():
            result.add_pass("有效配置验证")
        else:
            result.add_fail("有效配置验证", "应该返回 True")
    except Exception as e:
        result.add_fail("有效配置验证", str(e))

    # 测试 app_id 格式验证
    try:
        config = FeishuConfig(
            enabled=True,
            app_id="invalid_id",  # 不以 cli_ 开头
            app_secret="test"
        )
        config.is_valid()
        result.add_fail("app_id格式验证", "应该抛出异常")
    except Exception:
        result.add_pass("app_id格式验证")


async def test_sdk_import(result: TestResult):
    """测试 SDK 导入"""
    print("\n[测试 2] SDK 导入")

    try:
        from lark_oapi import im
        from lark_oapi.ws.client import Client, EventDispatcherHandler
        from lark_oapi.core.model import Config
        from lark_oapi.client import ImService
        result.add_pass("SDK 导入")
    except Exception as e:
        result.add_fail("SDK 导入", str(e))

    try:
        from lark_oapi import im
        # 检查消息 API
        req = im.v1.CreateMessageRequest
        if req:
            result.add_pass("消息 API 可用")
    except Exception as e:
        result.add_fail("消息 API", str(e))


async def test_message_creation(result: TestResult):
    """测试消息构建"""
    print("\n[测试 3] 消息构建")

    try:
        from lark_oapi import im

        # 测试创建发送消息请求 (正确方式)
        body = im.v1.CreateMessageRequestBody()
        body.receive_id = "ou_test123"
        body.msg_type = "text"
        body.content = json.dumps({"text": "Hello"})

        request = im.v1.CreateMessageRequest.builder() \
            .receive_id_type("open_id") \
            .request_body(body) \
            .build()

        if request.receive_id_type == "open_id" and request.request_body.receive_id == "ou_test123":
            result.add_pass("发送消息请求构建")
        else:
            result.add_fail("发送消息请求构建", "参数不匹配")
    except Exception as e:
        result.add_fail("发送消息请求构建", str(e))

    try:
        # 测试创建回复消息请求 (正确方式)
        body = im.v1.ReplyMessageRequestBody()
        body.msg_type = "text"
        body.content = json.dumps({"text": "Reply"})

        request = im.v1.ReplyMessageRequest.builder() \
            .message_id("om_test123") \
            .request_body(body) \
            .build()

        if request.message_id == "om_test123":
            result.add_pass("回复消息请求构建")
        else:
            result.add_fail("回复消息请求构建", "message_id 不匹配")
    except Exception as e:
        result.add_fail("回复消息请求构建", str(e))

    try:
        # 测试创建读取消息请求
        request = im.v1.GetMessageRequest.builder() \
            .message_id("om_test123") \
            .build()

        if request.message_id == "om_test123":
            result.add_pass("读取消息请求构建")
        else:
            result.add_fail("读取消息请求构建", "message_id 不匹配")
    except Exception as e:
        result.add_fail("读取消息请求构建", str(e))

    try:
        # 测试创建删除消息请求
        request = im.v1.DeleteMessageRequest.builder() \
            .message_id("om_test123") \
            .build()

        if request.message_id == "om_test123":
            result.add_pass("删除消息请求构建")
        else:
            result.add_fail("删除消息请求构建", "message_id 不匹配")
    except Exception as e:
        result.add_fail("删除消息请求构建", str(e))


async def test_feishu_skill_init(result: TestResult):
    """测试 FeishuSkill 初始化"""
    print("\n[测试 4] FeishuSkill 初始化")

    if not APP_ID or not APP_SECRET:
        result.add_fail("FeishuSkill 初始化", "缺少 FEISHU_APP_ID 或 FEISHU_APP_SECRET 环境变量")
        return

    try:
        config = FeishuConfig(
            enabled=True,
            app_id=APP_ID,
            app_secret=APP_SECRET
        )

        skill = FeishuSkill(config)

        if skill.is_enabled:
            result.add_pass("Skill 启用状态")
        else:
            result.add_fail("Skill 启用状态", "应该启用")

        if skill.platform_id == "feishu":
            result.add_pass("平台 ID")
        else:
            result.add_fail("平台 ID", "应该等于 feishu")

    except Exception as e:
        result.add_fail("FeishuSkill 初始化", str(e))


async def test_message_operations_with_real_api(result: TestResult):
    """测试真实 API 调用 (需要真实配置)"""
    print("\n[测试 5] 真实 API 消息操作")

    # 检查是否有测试用户 ID
    test_open_id = TEST_OPEN_ID
    if not test_open_id:
        # 尝试从日志中查找最近的发送消息获取 open_id
        try:
            with open("logs/feishu.log") as f:
                content = f.read()
                import re
                matches = re.findall(r'from=([a-z0-9_]+)', content)
                if matches:
                    test_open_id = matches[-1]
                    print(f"  ℹ️  从日志中发现测试用户: {test_open_id}")
        except:
            pass

    if not test_open_id:
        result.add_fail("真实 API 测试", "需要设置 FEISHU_TEST_OPEN_ID 环境变量")
        return

    try:
        from lark_oapi import im
        from lark_oapi.core.model import Config
        from lark_oapi.client import ImService
        from lark_oapi.api.im.v1.model import Emoji

        # 创建客户端
        config = Config()
        config.app_id = APP_ID
        config.app_secret = APP_SECRET
        im_service = ImService(config)

        # 测试发送消息 (正确方式)
        body = im.v1.CreateMessageRequestBody()
        body.receive_id = test_open_id
        body.msg_type = "text"
        body.content = json.dumps({"text": "[测试] 这是一条测试消息"})

        request = im.v1.CreateMessageRequest.builder() \
            .receive_id_type("open_id") \
            .request_body(body) \
            .build()

        response = im_service.v1.message.create(request)

        if response.success():
            msg_id = response.data.message_id
            result.add_pass(f"发送消息成功: {msg_id}")

            # 测试回复消息 (异步)
            try:
                reply_body = im.v1.ReplyMessageRequestBody()
                reply_body.msg_type = "text"
                reply_body.content = json.dumps({"text": "[测试] 这是回复"})

                reply_request = im.v1.ReplyMessageRequest.builder() \
                    .message_id(msg_id) \
                    .request_body(reply_body) \
                    .build()

                reply_response = await im_service.v1.message.areply(reply_request)
                if reply_response.success():
                    result.add_pass(f"回复消息成功")
                else:
                    result.add_fail("回复消息", reply_response.msg)
            except Exception as e:
                result.add_fail("回复消息", str(e))

            # 测试读取消息 (异步)
            try:
                get_request = im.v1.GetMessageRequest.builder() \
                    .message_id(msg_id) \
                    .build()

                get_response = await im_service.v1.message.aget(get_request)
                if get_response.success():
                    result.add_pass("读取消息成功")
                else:
                    result.add_fail("读取消息", get_response.msg)
            except Exception as e:
                result.add_fail("读取消息", str(e))

            # 测试添加反应 (异步)
            try:
                # 使用 Emoji 对象 (必须使用大写格式)
                emoji = Emoji.builder().emoji_type("SMILE").build()

                reaction_body = im.v1.CreateMessageReactionRequestBody()
                reaction_body.reaction_type = emoji

                reaction_request = im.v1.CreateMessageReactionRequest.builder() \
                    .message_id(msg_id) \
                    .request_body(reaction_body) \
                    .build()

                reaction_response = await im_service.v1.message_reaction.acreate(reaction_request)
                if reaction_response.success():
                    result.add_pass("添加反应成功")
                else:
                    result.add_fail("添加反应", reaction_response.msg)
            except Exception as e:
                result.add_fail("添加反应", str(e))

        else:
            result.add_fail("发送消息", response.msg)

    except Exception as e:
        result.add_fail("真实 API 测试", str(e))


async def main():
    """主测试函数"""
    print("="*50)
    print("Feishu Skill 自动化测试")
    print("="*50)

    # 检查环境变量
    print(f"\n环境配置:")
    print(f"  FEISHU_APP_ID: {'已设置' if APP_ID else '未设置'}")
    print(f"  FEISHU_APP_SECRET: {'已设置' if APP_SECRET else '未设置'}")
    print(f"  FEISHU_TEST_OPEN_ID: {'已设置' if TEST_OPEN_ID else '未设置'}")

    result = TestResult()

    # 运行测试
    await test_config_validation(result)
    await test_sdk_import(result)
    await test_message_creation(result)
    await test_feishu_skill_init(result)
    await test_message_operations_with_real_api(result)

    # 输出结果
    success = result.summary()

    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
