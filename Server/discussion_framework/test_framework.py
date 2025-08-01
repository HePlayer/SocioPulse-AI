"""
多Agent讨论框架测试
验证框架的基本功能和集成
"""

import asyncio
import logging
from unittest.mock import Mock, AsyncMock

from .continuous_controller import ContinuousDiscussionController
from .framework_manager import DiscussionFrameworkManager
from Item.Communication.message_types import ChatMessage, MessageType
from Item.Agentlib import Agent, AgentRole

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MockAgent:
    """模拟Agent用于测试"""
    
    def __init__(self, agent_id: str, name: str):
        self.component_id = agent_id
        self.name = name
        self.role = AgentRole.CHAT
        
    async def think(self, input_data: dict) -> dict:
        """模拟Agent思考过程"""
        user_input = input_data.get('user_input', '')
        
        # 简单的响应生成
        responses = [
            f"我是{self.name}，我认为{user_input[:20]}...是一个很有趣的话题。",
            f"作为{self.name}，我想补充一些观点...",
            f"从{self.name}的角度来看，这个问题需要深入思考。",
            f"{self.name}在这里，我同意之前的观点，并且想要添加...",
            f"让我以{self.name}的身份总结一下当前的讨论..."
        ]
        
        # 根据轮次选择不同的响应
        turn_number = input_data.get('room_context', {}).get('discussion_context', {}).get('discussion_turn', 1)
        response_index = (turn_number - 1) % len(responses)
        
        return {
            'success': True,
            'response': responses[response_index],
            'metadata': {
                'agent_name': self.name,
                'turn_number': turn_number
            }
        }


async def test_basic_framework():
    """测试基本框架功能"""
    logger.info("开始基本框架测试")
    
    # 创建模拟Agent
    agents = {
        'agent_1': MockAgent('agent_1', 'AI专家'),
        'agent_2': MockAgent('agent_2', '技术分析师'),
        'agent_3': MockAgent('agent_3', '产品经理')
    }
    
    # 创建控制器
    controller = ContinuousDiscussionController(
        max_turns=10,
        max_duration=60,
        enable_real_time_updates=True
    )
    
    # 设置事件处理器
    events_received = []
    
    async def event_handler(event):
        events_received.append(event)
        logger.info(f"收到事件: {event.event_type}")
    
    controller.subscribe_to_events(event_handler)
    
    # 创建初始消息
    initial_message = ChatMessage(
        sender_id="user",
        content="请讨论人工智能在未来5年的发展趋势",
        message_type=MessageType.TEXT
    )
    
    # 启动讨论
    result = await controller.start_discussion(
        room_id="test_room",
        topic="AI发展趋势讨论",
        participants=agents,
        initial_message=initial_message
    )
    
    if result['success']:
        logger.info(f"讨论启动成功: {result['session_id']}")
        
        # 让讨论运行一段时间
        await asyncio.sleep(5)
        
        # 获取状态
        status = controller.get_current_status()
        logger.info(f"讨论状态: {status['state']}, 轮次: {status['metrics']['total_turns']}")
        
        # 停止讨论
        stop_result = await controller.stop_discussion()
        logger.info(f"讨论停止: {stop_result}")
        
        # 检查事件
        logger.info(f"收到 {len(events_received)} 个事件")
        
        return True
    else:
        logger.error(f"讨论启动失败: {result['error']}")
        return False


async def test_framework_manager():
    """测试框架管理器"""
    logger.info("开始框架管理器测试")
    
    # 创建模拟Agent
    agents = {
        'agent_1': MockAgent('agent_1', 'AI专家'),
        'agent_2': MockAgent('agent_2', '技术分析师')
    }
    
    # 创建框架管理器
    manager = DiscussionFrameworkManager()
    
    # 创建初始消息
    initial_message = ChatMessage(
        sender_id="user",
        content="测试框架管理器功能",
        message_type=MessageType.TEXT
    )
    
    # 启动讨论
    result = await manager.start_enhanced_discussion(
        room_id="test_room_2",
        topic="框架管理器测试",
        participants=agents,
        initial_message=initial_message
    )
    
    if result['success']:
        logger.info(f"框架管理器讨论启动成功: {result['session_id']}")
        
        # 获取状态
        status = await manager.get_discussion_status("test_room_2")
        logger.info(f"管理器状态: {status.get('session_info', {}).get('session_id')}")
        
        # 获取所有状态
        all_statuses = await manager.get_all_discussion_statuses()
        logger.info(f"活跃会话数: {all_statuses['active_sessions']}")
        
        # 停止讨论
        await asyncio.sleep(2)
        stop_result = await manager.control_discussion("test_room_2", "stop")
        logger.info(f"管理器停止讨论: {stop_result}")
        
        return True
    else:
        logger.error(f"框架管理器讨论启动失败: {result['error']}")
        return False


async def test_svr_computation():
    """测试SVR计算"""
    logger.info("开始SVR计算测试")
    
    from .parallel_svr_engine import ParallelSVREngine, AgentSVRComputer
    from .discussion_context import DiscussionContext
    from Item.Communication.discussion_types import DiscussionSession
    
    # 创建模拟Agent
    agents = {
        'agent_1': MockAgent('agent_1', 'AI专家'),
        'agent_2': MockAgent('agent_2', '技术分析师')
    }
    
    # 创建讨论会话
    session = DiscussionSession(
        room_id="test_svr",
        topic="SVR测试",
        current_participants=list(agents.keys()),
        all_participants=list(agents.keys())
    )
    
    # 创建上下文
    context = DiscussionContext(session, agents)
    
    # 创建SVR引擎
    svr_engine = ParallelSVREngine()
    
    try:
        # 计算SVR
        svr_result = await svr_engine.compute_parallel_svr(context, agents)
        
        logger.info(f"SVR计算完成:")
        logger.info(f"  - 全局停止值: {svr_result.global_svr_metrics['global_stop_value']:.2f}")
        logger.info(f"  - 讨论质量: {svr_result.global_svr_metrics['discussion_quality']:.2f}")
        logger.info(f"  - 共识水平: {svr_result.global_svr_metrics['consensus_level']:.2f}")
        logger.info(f"  - 计算时间: {svr_result.computation_stats['total_time']:.3f}s")
        
        # 清理
        await context.cleanup()
        
        return True
    except Exception as e:
        logger.error(f"SVR计算测试失败: {e}")
        await context.cleanup()
        return False


async def run_all_tests():
    """运行所有测试"""
    logger.info("开始运行多Agent讨论框架测试套件")
    
    tests = [
        ("基本框架测试", test_basic_framework),
        ("框架管理器测试", test_framework_manager),
        ("SVR计算测试", test_svr_computation)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            logger.info(f"\n{'='*50}")
            logger.info(f"运行: {test_name}")
            logger.info(f"{'='*50}")
            
            result = await test_func()
            results.append((test_name, result))
            
            if result:
                logger.info(f"✅ {test_name} 通过")
            else:
                logger.error(f"❌ {test_name} 失败")
                
        except Exception as e:
            logger.error(f"❌ {test_name} 异常: {e}")
            results.append((test_name, False))
    
    # 总结
    logger.info(f"\n{'='*50}")
    logger.info("测试总结")
    logger.info(f"{'='*50}")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        logger.info(f"{test_name}: {status}")
    
    logger.info(f"\n总计: {passed}/{total} 测试通过")
    
    return passed == total


if __name__ == "__main__":
    # 运行测试
    success = asyncio.run(run_all_tests())
    
    if success:
        logger.info("🎉 所有测试通过！多Agent讨论框架准备就绪。")
    else:
        logger.error("💥 部分测试失败，请检查框架实现。")
