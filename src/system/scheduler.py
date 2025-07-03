#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
任务调度器模块
负责系统任务的调度和管理
"""

import time
import threading
import logging
from typing import Dict, List, Callable, Optional, Any
from dataclasses import dataclass
from enum import Enum
from queue import Queue, Empty
import uuid


class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPriority(Enum):
    """任务优先级枚举"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


@dataclass
class Task:
    """任务定义"""
    id: str
    name: str
    func: Callable
    args: tuple = ()
    kwargs: dict = None
    priority: TaskPriority = TaskPriority.NORMAL
    status: TaskStatus = TaskStatus.PENDING
    created_time: float = None
    start_time: float = None
    end_time: float = None
    result: Any = None
    error: str = None
    
    def __post_init__(self):
        if self.kwargs is None:
            self.kwargs = {}
        if self.created_time is None:
            self.created_time = time.time()
    
    def __lt__(self, other):
        """用于优先级队列排序"""
        return self.priority.value > other.priority.value


class TaskScheduler:
    """任务调度器"""
    
    def __init__(self, max_workers: int = 4):
        """初始化任务调度器"""
        self.max_workers = max_workers
        self.is_running = False
        self.workers = []
        self.task_queue = Queue()
        self.tasks = {}  # 任务存储
        self.completed_tasks = []  # 已完成任务历史
        self.lock = threading.RLock()
        
        # 统计信息
        self.stats = {
            'total_tasks': 0,
            'completed_tasks': 0,
            'failed_tasks': 0,
            'cancelled_tasks': 0,
            'running_tasks': 0
        }
        
        # 日志记录器
        self.logger = logging.getLogger(__name__)
        
        self.logger.info(f"任务调度器初始化完成，工作线程数: {max_workers}")
    
    def start(self) -> bool:
        """启动任务调度器"""
        try:
            if self.is_running:
                self.logger.warning("任务调度器已在运行")
                return True
            
            self.is_running = True
            
            # 创建工作线程
            for i in range(self.max_workers):
                worker = threading.Thread(
                    target=self._worker_loop,
                    name=f"TaskWorker-{i+1}",
                    daemon=True
                )
                worker.start()
                self.workers.append(worker)
            
            self.logger.info(f"任务调度器已启动，{len(self.workers)} 个工作线程")
            return True
            
        except Exception as e:
            self.logger.error(f"启动任务调度器失败: {e}")
            return False
    
    def stop(self, timeout: float = 5.0):
        """停止任务调度器"""
        try:
            if not self.is_running:
                return
            
            self.logger.info("正在停止任务调度器...")
            self.is_running = False
            
            # 等待工作线程结束
            start_time = time.time()
            for worker in self.workers:
                remaining_time = timeout - (time.time() - start_time)
                if remaining_time > 0:
                    worker.join(timeout=remaining_time)
            
            # 取消所有待处理任务
            self._cancel_pending_tasks()
            
            self.logger.info("任务调度器已停止")
            
        except Exception as e:
            self.logger.error(f"停止任务调度器失败: {e}")
    
    def submit_task(self, 
                   name: str, 
                   func: Callable, 
                   args: tuple = (), 
                   kwargs: dict = None,
                   priority: TaskPriority = TaskPriority.NORMAL) -> str:
        """提交任务"""
        try:
            if not self.is_running:
                raise RuntimeError("任务调度器未运行")
            
            # 创建任务
            task_id = str(uuid.uuid4())
            task = Task(
                id=task_id,
                name=name,
                func=func,
                args=args,
                kwargs=kwargs or {},
                priority=priority
            )
            
            with self.lock:
                self.tasks[task_id] = task
                self.stats['total_tasks'] += 1
            
            # 添加到队列
            self.task_queue.put(task)
            
            self.logger.info(f"任务已提交: {name} (ID: {task_id[:8]})")
            return task_id
            
        except Exception as e:
            self.logger.error(f"提交任务失败: {e}")
            raise
    
    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        try:
            with self.lock:
                task = self.tasks.get(task_id)
                if not task:
                    return False
                
                if task.status == TaskStatus.PENDING:
                    task.status = TaskStatus.CANCELLED
                    self.stats['cancelled_tasks'] += 1
                    self.logger.info(f"任务已取消: {task.name} (ID: {task_id[:8]})")
                    return True
                elif task.status == TaskStatus.RUNNING:
                    # 正在运行的任务无法取消，只能等待完成
                    self.logger.warning(f"无法取消正在运行的任务: {task.name}")
                    return False
                else:
                    self.logger.warning(f"任务状态不允许取消: {task.status}")
                    return False
                    
        except Exception as e:
            self.logger.error(f"取消任务失败: {e}")
            return False
    
    def get_task_status(self, task_id: str) -> Optional[Dict]:
        """获取任务状态"""
        with self.lock:
            task = self.tasks.get(task_id)
            if not task:
                return None
            
            return {
                'id': task.id,
                'name': task.name,
                'status': task.status.value,
                'priority': task.priority.value,
                'created_time': task.created_time,
                'start_time': task.start_time,
                'end_time': task.end_time,
                'result': task.result,
                'error': task.error,
                'duration': (task.end_time - task.start_time) if task.end_time and task.start_time else None
            }
    
    def get_all_tasks(self) -> List[Dict]:
        """获取所有任务状态"""
        with self.lock:
            return [self.get_task_status(task_id) for task_id in self.tasks.keys()]
    
    def get_running_tasks(self) -> List[Dict]:
        """获取正在运行的任务"""
        with self.lock:
            return [
                self.get_task_status(task_id) 
                for task_id, task in self.tasks.items() 
                if task.status == TaskStatus.RUNNING
            ]
    
    def get_pending_tasks(self) -> List[Dict]:
        """获取待处理任务"""
        with self.lock:
            return [
                self.get_task_status(task_id)
                for task_id, task in self.tasks.items()
                if task.status == TaskStatus.PENDING
            ]
    
    def get_statistics(self) -> Dict:
        """获取统计信息"""
        with self.lock:
            # 实时统计运行中任务数
            running_count = sum(
                1 for task in self.tasks.values() 
                if task.status == TaskStatus.RUNNING
            )
            self.stats['running_tasks'] = running_count
            
            return self.stats.copy()
    
    def clear_completed_tasks(self):
        """清除已完成的任务记录"""
        with self.lock:
            to_remove = []
            for task_id, task in self.tasks.items():
                if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                    to_remove.append(task_id)
            
            for task_id in to_remove:
                self.completed_tasks.append(self.tasks[task_id])
                del self.tasks[task_id]
            
            # 保持完成任务历史大小
            if len(self.completed_tasks) > 100:
                self.completed_tasks = self.completed_tasks[-100:]
            
            self.logger.info(f"已清除 {len(to_remove)} 个已完成任务")
    
    def _worker_loop(self):
        """工作线程循环"""
        thread_name = threading.current_thread().name
        self.logger.debug(f"工作线程 {thread_name} 已启动")
        
        while self.is_running:
            try:
                # 获取任务
                try:
                    task = self.task_queue.get(timeout=1.0)
                except Empty:
                    continue
                
                # 检查任务是否已被取消
                if task.status == TaskStatus.CANCELLED:
                    self.task_queue.task_done()
                    continue
                
                # 执行任务
                self._execute_task(task, thread_name)
                self.task_queue.task_done()
                
            except Exception as e:
                self.logger.error(f"工作线程 {thread_name} 发生错误: {e}")
        
        self.logger.debug(f"工作线程 {thread_name} 已停止")
    
    def _execute_task(self, task: Task, worker_name: str):
        """执行任务"""
        try:
            with self.lock:
                task.status = TaskStatus.RUNNING
                task.start_time = time.time()
            
            self.logger.info(f"[{worker_name}] 开始执行任务: {task.name}")
            
            # 执行任务函数
            result = task.func(*task.args, **task.kwargs)
            
            with self.lock:
                task.status = TaskStatus.COMPLETED
                task.end_time = time.time()
                task.result = result
                self.stats['completed_tasks'] += 1
            
            duration = task.end_time - task.start_time
            self.logger.info(f"[{worker_name}] 任务执行完成: {task.name} (耗时: {duration:.2f}s)")
            
        except Exception as e:
            with self.lock:
                task.status = TaskStatus.FAILED
                task.end_time = time.time()
                task.error = str(e)
                self.stats['failed_tasks'] += 1
            
            self.logger.error(f"[{worker_name}] 任务执行失败: {task.name}, 错误: {e}")
    
    def _cancel_pending_tasks(self):
        """取消所有待处理任务"""
        with self.lock:
            cancelled_count = 0
            for task in self.tasks.values():
                if task.status == TaskStatus.PENDING:
                    task.status = TaskStatus.CANCELLED
                    cancelled_count += 1
            
            self.stats['cancelled_tasks'] += cancelled_count
            if cancelled_count > 0:
                self.logger.info(f"已取消 {cancelled_count} 个待处理任务")
    
    def wait_for_completion(self, timeout: Optional[float] = None) -> bool:
        """等待所有任务完成"""
        try:
            if timeout:
                return self.task_queue.join(timeout=timeout)
            else:
                self.task_queue.join()
                return True
        except:
            return False
    
    def __del__(self):
        """析构函数"""
        if hasattr(self, 'is_running') and self.is_running:
            self.stop()


# 创建全局调度器实例
task_scheduler = TaskScheduler()


# 导出接口
__all__ = [
    'TaskScheduler',
    'Task',
    'TaskStatus', 
    'TaskPriority',
    'task_scheduler'
] 