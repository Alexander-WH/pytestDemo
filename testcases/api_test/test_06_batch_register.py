import pytest
import allure
import json
import os
from operation.user import get_one_user_info
from common.logger import logger

# 定位到项目根目录，再找到 data/generated_users.json
BASE_PATH = os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
JSON_PATH = os.path.join(BASE_PATH, "data", "generated_users.json")

# 【核心】读取 JSON 文件，把它变成一个列表，传给 parametrize
with open(JSON_PATH, encoding='utf-8') as f:
    generated_users = json.load(f)


@allure.epic("针对批量随机数据的测试")
@allure.feature("批量数据校验模块")
class TestBatchGeneratedUsers:

    @allure.story("用例--校验随机生成的用户数据")
    @allure.description("读取 generated_users.json，逐条校验随机生成的用户是否真正落库")
    @allure.title("校验随机用户：{user_data[username]}")
    # 【核心】把 JSON 里的 50 条数据，变成 50 个独立的测试用例
    @pytest.mark.parametrize("user_data", generated_users)
    def test_check_generated_user(self, user_data):
        username = user_data["username"]

        with allure.step(f"步骤1 ==>> 查询用户：{username}"):
            result = get_one_user_info(username)

        with allure.step("步骤2 ==>> 断言接口返回结果"):
            assert result.success is True, f"用户 {username} 查询失败: {result.error}"
            assert result.response.json()["code"] == 0
            assert result.response.json()["data"][0]["username"] == username
            logger.info(f"✅ 校验通过: {username}")