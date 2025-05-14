from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from datetime import datetime
import json
import os

@register("ordering_food", "Axl", "社群订餐管理插件，支持接收订单、自动编号、订单汇总等功能", "v1.0.0", "https://github.com/QWqwzx/astrbot_plugin_Ordering-food.git")
class OrderingFoodPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        # 存储订单信息的列表
        self.orders = []
        # 当前订单ID计数
        self.current_id = 1
        # 数据文件路径
        self.data_file = None
    
    async def initialize(self):
        """插件初始化，加载历史订单数据"""
        logger.info("订餐管理插件初始化中...")
        # 获取插件数据目录并创建数据文件路径
        data_dir = self.context.get_plugin_data_dir()
        self.data_file = os.path.join(data_dir, "orders.json")
        
        # 尝试加载历史订单数据
        await self.load_orders()
        logger.info(f"订餐管理插件已初始化，当前订单数量: {len(self.orders)}")
    
    # 通用消息处理（包括@机器人的所有消息）
    @filter.command("")
    async def handle_message(self, event: AstrMessageEvent):
        """处理所有消息，包括订单、初始化和汇总"""
        # 仅在群聊中生效
        if not event.is_group():
            return
            
        # 检查是否@了机器人，如果没有则直接返回
        if not event.is_to_me():
            return
            
        message_str = event.message_str.strip()
        user_name = event.get_sender_name()
        user_id = event.get_sender_id()
        
        # 处理初始化命令
        if message_str == "初始化":
            self.orders = []
            self.current_id = 1
            await self.save_orders()
            logger.info("订单记录已初始化")
            yield event.plain_result("订单记录已初始化,历史记录清0")
            return
        
        # 处理汇总命令
        if message_str == "汇总":
            logger.info("执行订单汇总")
            if not self.orders:
                yield event.plain_result("当前没有订单记录")
                return
                
            summary = "订单汇总：\n"
            for order in self.orders:
                summary += f"编号：{order['order_id']}\n"
                summary += f"用户：{order['user_name']}\n"
                summary += f"内容：{order['content']}\n"
                summary += f"时间：{order['time']}\n"
                summary += "-------------\n"
                
            yield event.plain_result(summary)
            return
        
        # 处理普通订单
        order_id = f"{self.current_id:03d}"  # 格式化为001、002...
        self.current_id += 1
        
        # 创建订单记录
        order = {
            "order_id": order_id,
            "user_id": user_id,
            "user_name": user_name,
            "content": message_str,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        self.orders.append(order)
        
        # 保存订单数据
        await self.save_orders()
        
        # 生成回复内容
        short_content = message_str[:20] + "..." if len(message_str) > 20 else message_str
        reply_content = f"{short_content} 编号：{order_id}"
        
        logger.info(f"新订单已记录，编号: {order_id}, 用户: {user_name}")
        
        # 回复用户
        yield event.quote_result(reply_content)
    
    async def save_orders(self):
        """保存订单数据到文件"""
        try:
            # 确保数据目录存在
            os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
            
            # 保存数据
            with open(self.data_file, "w", encoding="utf-8") as f:
                json.dump({
                    "orders": self.orders,
                    "current_id": self.current_id
                }, f, ensure_ascii=False, indent=2)
                
            logger.info(f"订单数据已保存，当前订单数量: {len(self.orders)}")
        except Exception as e:
            logger.error(f"保存订单数据失败: {str(e)}")
    
    async def load_orders(self):
        """从文件加载订单数据"""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.orders = data.get("orders", [])
                    self.current_id = data.get("current_id", 1)
                logger.info(f"订单数据已加载，当前订单数量: {len(self.orders)}")
            else:
                logger.info("未找到历史订单数据，使用空列表初始化")
        except Exception as e:
            logger.error(f"加载订单数据失败: {str(e)}")
            self.orders = []
            self.current_id = 1
    
    async def terminate(self):
        """插件卸载时调用，保存当前数据"""
        logger.info("订餐管理插件正在卸载，保存数据中...")
        await self.save_orders()
        logger.info("订餐管理插件已卸载")
