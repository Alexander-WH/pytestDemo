import json
import pytest
import os
import allure
from api.user import user
from common.mysql_operate import db
from common.read_data import data
from common.logger import logger
from faker import Faker

BASE_PATH = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))


fake = Faker('zh_CN') # 初始化中文环境
@pytest.fixture(scope="function")
def random_telephone():
    """生成一个随机的、绝对唯一的手机号"""
    return fake.phone_number()

def get_data(yaml_file_name):
    try:
        data_file_path = os.path.join(BASE_PATH, "data", yaml_file_name)
        yaml_data = data.load_yaml(data_file_path)
    except Exception as ex:
        pytest.skip(str(ex))
    else:
        return yaml_data

def get_json_data(json_file_name):
    try:
        data_file_path = os.path.join(BASE_PATH, "data", json_file_name)
        with open(data_file_path, encoding="utf-8") as f:
            json_data = json.load(f)
    except Exception as ex:
        pytest.skip(str(ex))
    else:
        return json_data

# 加载你的用户json数据
generated_users = get_json_data("generated_users.json")


base_data = get_data("base_data.yml")
api_data = get_data("api_test_data.yml")
scenario_data = get_data("scenario_test_data.yml")


@allure.step("前置步骤 ==>> 清理数据")
def step_first():
    logger.info("******************************")
    logger.info("前置步骤开始 ==>> 清理数据")


@allure.step("后置步骤 ==>> 清理数据")
def step_last():
    logger.info("后置步骤开始 ==>> 清理数据")


@allure.step("前置步骤 ==>> 管理员用户登录")
def step_login(username, password):
    logger.info("前置步骤 ==>> 管理员 {} 登录，返回信息 为：{}".format(username, password))


@pytest.fixture(scope="session")
def login_fixture():
    username = base_data["init_admin_user"]["username"]
    password = base_data["init_admin_user"]["password"]
    header = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    payload = {
        "username": username,
        "password": password
    }
    loginInfo = user.login(data=payload, headers=header)
    step_login(username, password)

    res_json = loginInfo.json()
    # 增加这行断言，如果登录失败，直接报出后端返回的错误信息
    assert res_json.get("code") == 0, f"管理员登录失败！接口返回：{res_json}"

    yield res_json


@pytest.fixture(scope="function")
def insert_delete_user():
    """删除用户前，先在数据库插入一条用户数据"""
    insert_sql = base_data["init_sql"]["insert_delete_user"][0]
    db.execute_db(insert_sql)
    step_first()
    logger.info("删除用户操作：插入新用户--准备用于删除用户")
    logger.info("执行前置SQL：{}".format(insert_sql))
    yield
    # 因为有些情况是不给删除管理员用户的，这种情况需要手动清理上面插入的数据
    del_sql = base_data["init_sql"]["insert_delete_user"][1]
    db.execute_db(del_sql)
    step_last()
    logger.info("删除用户操作：手工清理处理失败的数据")
    logger.info("执行后置SQL：{}".format(del_sql))


@pytest.fixture(scope="function")
def delete_register_user():
    """注册用户前，先删除数据，用例执行之后，再次删除以清理数据"""
    del_sql = base_data["init_sql"]["delete_register_user"]
    db.execute_db(del_sql)
    step_first()
    logger.info("注册用户操作：清理用户--准备注册新用户")
    logger.info("执行前置SQL：{}".format(del_sql))
    yield
    db.execute_db(del_sql)
    step_last()
    logger.info("注册用户操作：删除注册的用户")
    logger.info("执行后置SQL：{}".format(del_sql))


@pytest.fixture(scope="function")
def update_user_telephone():
    """修改用户前，确保 id=100 的靶子用户存在，然后修改它的手机号"""
    # 【核心修复】前置自动补数据：保证 id=100 的用户永远存在（ON DUPLICATE KEY UPDATE 表示如果已存在就更新，不存在就插入）
    insert_sql = """INSERT INTO user (id, username, password, role, sex, telephone, address) 
                    VALUES (100, 'update_target', '123456', 1, 1, '13000000000', '测试地址')
                    ON DUPLICATE KEY UPDATE username='update_target'"""
    db.execute_db(insert_sql)
    # 【核心修复】前置强制清理：防止上一次测试残留的数据导致唯一键冲突
    clean_sql = "DELETE FROM user WHERE telephone IN ('13800001111', '1350001001', '13800001111')"
    db.execute_db(clean_sql)
    logger.info("前置清理冲突手机号完成")

    # 原来的逻辑保持不变
    update_sql = base_data["init_sql"]["update_user_telephone"]
    db.execute_db(update_sql)
    step_first()
    logger.info("修改用户操作：手工修改用户的手机号，以便用例重复执行")
    logger.info("执行SQL：{}".format(update_sql))


@pytest.fixture(scope="session", autouse=True)
def prepare_admin_user():
    """全局前置：自动检查管理员是否存在，不存在则注册，并自动提权"""
    username = base_data["init_admin_user"]["username"]
    password = base_data["init_admin_user"]["password"]

    logger.info("========== 开始检查管理员账号环境 ==========")

    # 1. 查数据库，看管理员在不在
    sql_check = "SELECT * FROM user WHERE username = %s"
    res = db.select_db(sql_check, (username,))

    if not res:
        # 2. 如果不在，自动调用注册接口（注意：这里需要传 JSON 格式）
        logger.info(f"管理员 {username} 不存在，正在自动注册...")
        user.register(json={
            "username": username,
            "password": password,
            "sex": "0",
            "telephone": "13800138000",
            "address": "北京市"
        })

    # 3. 不管在不在，强制提权，保证 role=0
    sql_update_role = "UPDATE user SET role = 0 WHERE username = %s"
    db.execute_db(sql_update_role, (username,))
    logger.info(f"管理员 {username} 提权完成（role=0），环境准备就绪！")

    # 4. 顺便把修改接口需要的专属靶子（id=100）也准备好
    sql_insert_target = """INSERT INTO user (id, username, password, role, sex, telephone, address)
                           VALUES (100, 'update_target', '123456', 1, 1, '13000000000', '测试地址') ON DUPLICATE KEY \
    UPDATE username='update_target'"""
    db.execute_db(sql_insert_target)
    logger.info("修改接口专属靶子（id=100）准备就绪！")
