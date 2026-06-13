# -*- coding: utf-8 -*-
import os
import time
import json
import base64
import random
import requests
import ddddocr
from bs4 import BeautifulSoup
from datetime import datetime
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

# ==========================================
# 模块：全局认证中心与门户信息获取
# ==========================================
class NuistCAS:
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        })
        self.cas_login_url = "https://authserver.nuist.edu.cn/authserver/login"
        self.ocr = ddddocr.DdddOcr(show_ad=False)

    def _encrypt_password(self, password, key):
        """AES 加密密码 (前端 encrypt.js 逆向)"""
        def random_string(length):
            chars = "ABCDEFGHJKMNPQRSTWXYZabcdefhijkmnprstwxyz2345678"
            return ''.join(random.choice(chars) for _ in range(length))

        random_prefix = random_string(64)
        iv = random_string(16)
        text = (random_prefix + password).encode('utf-8')
        key = key.strip().encode('utf-8')
        iv = iv.encode('utf-8')
        
        # PKCS7 填充
        pad = AES.block_size - len(text) % AES.block_size
        text += bytes([pad] * pad)
        
        cipher = AES.new(key, AES.MODE_CBC, iv)
        return base64.b64encode(cipher.encrypt(text)).decode('utf-8')

    def _get_and_recognize_captcha(self):
        """
        独立的验证码获取与识别函数
        :return: 识别出的验证码字符串 (若失败返回 None)
        """
        print("🧩 [验证码] 正在获取并识别验证码...")
        # 拼接时间戳防止缓存
        timestamp = int(datetime.now().timestamp() * 1000)
        captcha_url = f'https://authserver.nuist.edu.cn/authserver/getCaptcha.htl?{timestamp}'
        
        try:
            # 请求图片
            captcha_img_resp = self.session.get(captcha_url, timeout=5)
            # 交由 ddddocr 识别
            captcha_text = self.ocr.classification(captcha_img_resp.content)
            print(f"📝 [验证码] 识别结果: {captcha_text}")
            return captcha_text
        except Exception as e:
            print(f"❌ [验证码] 获取或识别失败: {e}")
            return None

    def login(self):
        """核心登录逻辑：获取全局 Cookie (TGC)"""
        print("🚪 [系统] 正在访问信息门户大门...")
        
        # 1. 获取执行参数 (execution) 和动态加密盐 (pwdEncryptSalt)
        try:
            resp = self.session.get(self.cas_login_url, timeout=10)
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            execution_tag = soup.find('input', id="execution")
            salt_tag = soup.find('input', id="pwdEncryptSalt")
            
            if not execution_tag or not salt_tag:
                print("❌ [错误] 无法获取页面加密参数，可能网络异常或已登录。")
                return False
                
            execution = execution_tag["value"]
            pwdEncryptSalt = salt_tag["value"]
        except Exception as e:
            print(f"❌ [错误] 访问登录页异常: {e}")
            return False

        # 2. 调用独立函数获取验证码
        captcha = self._get_and_recognize_captcha()
        if not captcha:
            print("❌ [错误] 验证码环节中断，停止登录。")
            return False

        # 3. 提交登录表单
        print("🔑 [系统] 正在加密并提交登录表单...")
        enc_password = self._encrypt_password(self.password, pwdEncryptSalt)
        login_data = {
            'username': self.username,
            'password': enc_password,
            'captcha': captcha,
            '_eventId': 'submit',
            'cllt': 'userNameLogin',
            'dllt': 'generalLogin',
            'lt': '',
            'execution': execution,
        }

        # 允许重定向，让服务端种植 Cookie
        self.session.post(
            self.cas_login_url, 
            data=login_data, 
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            allow_redirects=True
        )

        # 4. 验证是否拿到全局通行证 (CASTGC)
        if 'CASTGC' in self.session.cookies.get_dict():
            print("✅ [系统] 登录成功！已获取全局通行证(TGC)。\n" + "-"*40)
            return True
        else:
            print("❌ [系统] 登录失败！请检查账号密码或验证码是否识别错误。")
            return False

    def get_user_info(self):
        """获取个人信息 (打通信息门户子系统)"""
        print("👤 [系统] 正在请求个人信息接口...")
        
        # 1. 核心步骤：携带TGC访问带有 service 的链接，进行 SSO 单点登录，获取 i.nuist.edu.cn 的 Cookie
        sso_url = "https://authserver.nuist.edu.cn/authserver/login?service=https%3A%2F%2Fi.nuist.edu.cn%2Flogin"
        self.session.get(sso_url)
        
        # 2. 访问获取用户信息的接口
        timestamp = time.time()
        api_url = f"https://i.nuist.edu.cn/getLoginUser?_t={timestamp}"
        
        try:
            response = self.session.get(api_url)
            data = response.json()
            
            if data.get("errcode") == "0":
                user_data = data.get("data", {})
                print("🎉 [成功] 成功获取到用户信息：")
                print(f"   🧑‍🎓 姓名:     {user_data.get('userName')}")
                print(f"   🆔 学号:     {user_data.get('userAccount')}")
                print(f"   🏫 学院/部门: {user_data.get('deptName')}")
                print(f"   ✉️ 邮箱:     {user_data.get('email')}")
                print(f"   🏷️ 身份:     {user_data.get('categoryName')}")
                print("-" * 40)
                return user_data
            else:
                print(f"❌ [失败] 获取信息失败，接口返回: {data.get('errmsg')}")
                return None
        except Exception as e:
            print(f"❌ [异常] 解析个人信息接口出错: {e}")
            return None


# ==========================================
# 测试运行
# ==========================================
if __name__ == "__main__":
    # 替换为你的真实学号和密码
    bot = NuistCAS("2024XXXXXXXX", "YourPasswordHere")
    
    if bot.login():
        bot.get_user_info()
