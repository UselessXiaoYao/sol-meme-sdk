# 安装指南

## 方式一：从 PyPI 安装（推荐）

```bash
pip install sol-meme-sdk
```

## 方式二：从 GitHub 安装最新版本

```bash
pip install git+https://github.com/UselessXiaoYao/sol-meme-sdk.git
```

## 方式三：从源码安装

```bash
# 克隆仓库
git clone https://github.com/UselessXiaoYao/sol-meme-sdk.git
cd sol-meme-sdk

# 安装开发版本
pip install -e .

# 安装开发依赖
pip install -e .[dev]
```

## 系统要求

- **Python**: 3.8 或更高版本
- **操作系统**: Windows, macOS, Linux
- **网络**: 需要连接 Solana 区块链网络

## 依赖项

SDK 会自动安装以下依赖：

- `solana>=0.30.0` - Solana Python SDK
- `solders>=0.18.0` - Solana 序列化工具
- `aiohttp>=3.8.0` - 异步 HTTP 客户端
- `pydantic>=2.0.0` - 数据验证
- `base58>=2.1.0` - Base58 编码
- `python-dotenv>=1.0.0` - 环境变量管理

## 快速验证安装

```python
import asyncio
from sol_meme_sdk import SolMemeClient

async def test_installation():
    client = SolMemeClient()
    print("✅ SDK 安装成功！")

asyncio.run(test_installation())
```

## 配置 API 密钥

1. 获取 Jupiter API 密钥：https://portal.jup.ag/
2. 创建 `.env` 文件：

```bash
JUPITER_API_KEY=your_api_key_here
SOLANA_NETWORK=mainnet-beta
```

## 故障排除

### 安装失败

- **检查 Python 版本**: `python --version`
- **更新 pip**: `pip install --upgrade pip`
- **使用虚拟环境**: 推荐使用 `venv` 或 `conda`

### 网络连接问题

- **检查防火墙**: 确保可以访问 Solana RPC 节点
- **更换 RPC**: 在配置中使用不同的 RPC URL
- **使用代理**: 如果有网络限制，配置代理

### 依赖冲突

- **创建新环境**: 使用新的虚拟环境
- **检查依赖**: `pip list | grep solana`
- **降级版本**: 如果遇到兼容性问题

## 获取帮助

- **GitHub Issues**: https://github.com/UselessXiaoYao/sol-meme-sdk/issues
- **文档**: 查看 `README.md` 和 `examples/` 目录