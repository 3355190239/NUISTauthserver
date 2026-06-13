# NUIST 统一身份认证登录分析与实现 (NUISTauthserver)

> ⚠️ **免责声明**
> 本项目涉及的所有技术分析、接口说明及相关代码，仅供**学习与技术交流**使用。请在使用时严格遵守相关法律法规，请勿用于任何商业用途、恶意攻击或破坏系统的行为。
> （注：本项目沉淀的技术分析与逆向思路将予以保留，欢迎有能力、感兴趣的同学以此为参考，深入研究南信大相关系统的加密与自动化。）

![项目说明图](https://github.com/user-attachments/assets/04226652-3881-4bbd-8177-035ef288d8f4)

- **统一登录地址：** [https://i.nuist.edu.cn/](https://i.nuist.edu.cn/)
- **项目仓库：** [3355190239/NUISTauthserver](https://github.com/3355190239/NUISTauthserver)

---

## 💡 项目版本说明

为了方便不同开发需求和运行环境的同学研究，本项目目前实现了**两种技术路线**来处理密码加密：

### 1. JS 本地调用加密版 🛠️
* **原理**：直接将信息门户前端的 `encrypt.js` 加密文件完整复制到本地，利用 Python 的 `execjs`（或其他 JS 运行时桥接库）直接调用原汁原味的前端加密函数。
* **优点**：完美还原前端行为，若学校未来只微调混淆逻辑而不改动大算法，该版本具有极强的兼容性和容错率。
* **缺点**：运行环境需要依赖本地安装有 Node.js 等 JavaScript 执行环境。

### 2. 纯 Python 重构加密版 🐍
* **原理**：通过逆向分析前端的加密逻辑与填充规则，完全使用 Python 原生加密库（`pycryptodome`）重写了整个 **AES-CBC** 加密流程。
* **优点**：完全脱离对 JavaScript 运行环境的依赖，执行效率极高，跨平台便携性极佳（支持直接打包或在无 Node 纯净服务器运行）。
* **缺点**：逆向重构成本较高，需精确匹配前端的随机前缀混淆和 IV 生成规则。

---

## 🔍 统一登录流程内核剖析

无论使用哪一个版本，其底层的 CAS（Central Authentication Service）会话握手流程都是一致的，核心交互流程共分为以下四个阶段：


| 阶段 | 动作方向 | 参与方 | 关键数据 / 目的 |
|------|----------|--------|------------------|
| 1 | 浏览器 → CAS服务器 | CAS服务器 | `GET` 登录页，从 HTML/JS 中提取 `execution` 和动态加密盐 `pwdEncryptSalt` |
| 2 | 浏览器 → CAS服务器 | CAS服务器 | `GET` 验证码图片流 |
| 3 | 浏览器 → OCR识别模块 | 本地OCR引擎 | 对验证码图片进行自动化文本识别（或用户手动输入） |
| 4 | 浏览器 → 前端加密模块 | 前端加密模块（JS） | 明文密码 + 随机混淆 → 密文（双版本加密） |
| 5 | 浏览器 → CAS服务器 | CAS服务器 | `POST` 表单提交（用户名、密文密码、`execution`、验证码），认证成功后服务器种植 `TGC` Cookie |

### 详细步骤与抓包分析

#### 步骤 1：初始化会话与凭证抓取
* **请求 URL**：`https://authserver.nuist.edu.cn/authserver/login`
* **请求方法**：`GET`
* **返回结果**：HTML 网页源文件

![获取页面隐藏信息](https://github.com/user-attachments/assets/b13beb0d-c16b-41f7-849c-0b3c7063f63d)

* **核心逻辑**：必须维持单一个体会话（`requests.Session()`）。从返回的网页 HTML 源码中，利用 `BeautifulSoup` 动态提取两个关键隐藏表单参数：
  1. `execution`：会话流水执行步进凭证（用于最终 POST 的表单）。
  2. `pwdEncryptSalt`：服务器为本次登录分配的动态加密盐值。

#### 步骤 2：获取与识别验证码
* **请求 URL**：`https://authserver.nuist.edu.cn/authserver/getCaptcha.htl?[时间戳]`
* **核心逻辑**：利用上一步由 `Session` 建立并持有的 `Cookie` 去请求验证码接口，确保会话一致。验证码请求链接中包含一个动态时间戳（Timestamp），用以避免浏览器缓存。
* **自动化**：获取到图片二进制流后，流式输入给本地 `ddddocr` 引擎进行高精度识别。

![验证码请求分析](https://github.com/user-attachments/assets/f9e882b5-98d2-4ab9-9bad-cdb122106664)

#### 步骤 3：核心逆向——密码 AES 加密
通过在前端代码中下断点分析发现，用户输入的明文密码与第一步获取到的 `pwdEncryptSalt`（盐值）会共同作为参数传入 `encryptPassword` 函数中：
```javascript
$("#saltPassword").val(encryptPassword($(LOGIN_PASSWORD_ID).val(), $("#pwdEncryptSalt").val()));

```

* **纯 Python 版算法细节**：
* **混淆前缀**：随机生成一串 64 位长度的特定字符集字符串，拼接在用户输入的明文密码之前。
* **初始向量 (IV)**：随机生成 16 位长度的特定字符集字符串。
* **填充模式**：采用 `PKCS7` 标准将数据对齐至 AES 块大小（16 字节）。
* **加密算法**：使用网页端抓取到的 `pwdEncryptSalt` 作为 Key，采用 **AES-CBC** 模式进行加密，最终将结果进行 `Base64` 编码输出。



#### 步骤 4：发起登录请求

* **请求 URL**：`https://authserver.nuist.edu.cn/authserver/login?service=https%3A%2F%2Fi.nuist.edu.cn%2Flogin%23%2F`
* **请求方法**：`POST`
* **请求 Payload (表单数据字段)**：

| 关键字 (Key) | 类型 (Type) | 信息说明 (Description) | 备注 (Note) |
| --- | --- | --- | --- |
| `username` | string | 学号 / 工号 | 登录所需的标准账户名 |
| `password` | string | 加密后的密文密码 | 经过 JS 或 Python 模块计算后的 Base64 密文 |
| `captcha` | string | 验证码识别结果 | OCR 引擎返回的文本结果 |
| `execution` | string | 流程执行控制凭证 | 从步骤 1 初始化 GET 页面中动态提取的值 |
| `_eventId` | string | 提交事件类型 | 固定值为 `'submit'` |
| `cllt` | string | 登录视图类型 | 固定值为 `'userNameLogin'` |
| `dllt` | string | 登录处理类型 | 固定值为 `'generalLogin'` |
| `lt` | string | 留空参数 | 默认为空字符串 `''` |

* **状态判定**：若登录成功，服务器会在当前 Session 中种植名为 `CASTGC` 的 Cookie。该 Cookie 是通行全校各大子系统的“全局全局通行证(TGC)”，后续请求只需持有该 Session 即可实行免密跨系统访问。

---

## 📝 更新日志 (Logs)

### [v1.1.0] - 当前版本

* **✨ 新增特性**：成功逆向前端 `encrypt.js`，上线了纯 Python 重构密码加密算法的版本，解耦了对本地 Node.js/JS 环境的依赖，极大提高了脚本的跨平台便携性。
* **📝 文档重构**：规范化并重新排版了 README 文档，将项目拆分为“双版本技术路线”介绍，并梳理了精细化的 AES 加密算法细节。

### [v1.0.0] - 历史版本

* **🎉 基础实现**：完成了基于本地 JS 文件加载（通过 `execjs` 库）的统一身份认证密码加密方案。
* **⚙️ 流程打通**：实现了从 Session 初始化、获取 `pwdEncryptSalt` & `execution`、验证码 OCR 自动化识别到最终 POST 模拟登录的完整闭环链路。
