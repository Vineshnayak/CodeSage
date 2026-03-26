"""
File watcher to automatically re-index the graph and vector store.
"""
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from pathlib import Path

from core.parser import ProjectParser
from core.knowledge_graph import KnowledgeGraph
from core.embeddings import EmbeddingStore

class CodebaseWatcher(FileSystemEventHandler):
    def __init__(self, root_dir: str, kg: KnowledgeGraph, vs: EmbeddingStore, parser: ProjectParser):
        self.root_dir = root_dir
        self.kg = kg
        self.vs = vs
        self.parser = parser
        self.last_triggered = 0

    def process_change(self):
        # Debounce multiple rapid events
        now = time.time()
        if now - self.last_triggered < 2.0:
            return
        self.last_triggered = now

        print("\n[Watcher] Codebase change detected. Re-indexing...")
        
        # 1. Parse Project
        modules = self.parser.parse_project()
        
        # 2. Update Graph
        self.kg.build_from_modules(modules)
        self.kg.save()
        
        # 3. Update Vector Store
        self.vs.clear() # Simplistic implementation: wipe and rebuild
        for mod in modules:
            filepath = Path(self.root_dir) / mod.filepath
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
                self.vs.chunk_and_embed_file(mod.filepath, content)
            except Exception:
                continue
        self.vs.save()
        
        print("[Watcher] Re-indexing complete.")

    def on_modified(self, event):
        if event.src_path.endswith(".py"):
            self.process_change()

    def on_created(self, event):
        if event.src_path.endswith(".py"):
            self.process_change()

    def on_deleted(self, event):
        if event.src_path.endswith(".py"):
            self.process_change()

def start_watcher(root_dir: str, kg: KnowledgeGraph, vs: EmbeddingStore, parser: ProjectParser):
    event_handler = CodebaseWatcher(root_dir, kg, vs, parser)
    observer = Observer()
    observer.schedule(event_handler, path=root_dir, recursive=True)
    observer.start()
    return observer
