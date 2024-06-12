from collections import defaultdict
import json
import sys
from pathlib import Path

import networkx as nx
import matplotlib.pyplot as plt


class DependencyParser():
    def __init__(self) -> None:
        self.directories = {}
        self.current_path_name = ""
        self._configure()

    def parse(self, directory: str):
        path = Path(directory)
        if not path.exists():
            raise ValueError(f"Path does not exist: {path}")
        if not path.is_dir():
            raise ValueError(f"Path is not a directory: {path}")

        self.directory = path.name
        self.directories[self.directory] = defaultdict(list)
        self._traverse_directory(path)

    def get_dependencies(self):
        return self.directories

    def _configure(self):
        with open('config.json', 'r') as f:
            config = json.load(f)
        self.ignore_dirs = set(config['ignore_dirs'])
        self.ignore_libs = set(sys.stdlib_module_names) if config['ignore_stdlib'] else set()
        self.ignore_libs |= set(config['ignore_libs'])

    def _get_file_dependencies(self, file):
        directory_dict = self.directories[self.directory]
        full_file_path = file.as_posix()
        file_path = full_file_path[full_file_path.index(self.directory):]

        if not file.name.endswith('.py'):
            return
        with file.open('r') as f:
            for line in f.readlines():
                line = line.strip()

                if line.startswith('import '):
                    module = line.split()[1]
                    if module.split('.')[0] in self.ignore_libs:
                        continue

                    directory_dict[file_path].append(module)

                elif line.startswith('from '):
                    tokens = line.split()

                    module = tokens[1]
                    if module.split('.')[0] in self.ignore_libs:
                        continue

                    if tokens[3] == '*':
                        directory_dict[file_path].append(tokens[1])
                        continue

                    deps = tokens[3:]
                    formatted_deps = []
                    skip_one = False
                    for dep in deps:
                        if skip_one:
                            skip_one = False
                            continue
                        if dep == "as":
                            skip_one = True
                            continue
                        formatted_deps.append(f"{tokens[1]}.{dep.replace(',', '').replace(' ', '')}")
                    directory_dict[file_path] += formatted_deps

    def _traverse_directory(self, path):
        for file in path.iterdir():
            if file.is_dir():
                if file.name in self.ignore_dirs:
                    continue
                self._traverse_directory(file)
            elif file.is_file():
                self._get_file_dependencies(file)


class DependencyVisualizer:
    def __init__(self, dependecies) -> None:
        self.dependencies = dependecies
        self.graph = nx.Graph()

    def plot(self):
        color_map = []

        nodes = set()
        for directory in self.dependencies:
            self.graph.add_node(directory)
            if directory not in nodes:
                color_map.append("red")
            nodes.add(directory)
            for file in self.dependencies[directory]:
                self.graph.add_edge(directory, file)
                self.graph.add_node(file)
                if file not in nodes:
                    color_map.append("orange")
                nodes.add(file)
                for dep in self.dependencies[directory][file]:
                    self.graph.add_edge(file, dep)
                    self.graph.add_node(dep)
                    if dep not in nodes:
                        color_map.append("yellow")
                    nodes.add(dep)

        nx.draw(self.graph, node_color=color_map, with_labels=True)
        plt.show()


if __name__ == "__main__":
    if len(sys.argv) == 1:
        print("Usage: itdepends <project_dir>+")
        exit()

    project_dirs = sys.argv[1:]

    dp = DependencyParser()
    for project_dir in project_dirs:
        dp.parse(project_dir)
    print(json.dumps(dp.get_dependencies(), indent=2))

    dv = DependencyVisualizer(dp.get_dependencies())
    dv.plot()

