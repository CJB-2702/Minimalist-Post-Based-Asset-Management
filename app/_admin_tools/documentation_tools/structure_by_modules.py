#!/usr/bin/env python3
"""
Script to build module-specific structure summaries
Creates separate documents for each major module (assets, core, dispatching, inventory, maintenance)
"""
import ast
import json
from pathlib import Path
from typing import Dict, List, Any, Set

def extract_classes_from_file(file_path: Path) -> List[Dict[str, str]]:
    """Extract class definitions from a Python file"""
    classes = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        tree = ast.parse(content, filename=str(file_path))
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Get class docstring if available
                docstring = ast.get_docstring(node) or ""
                description = docstring.split('\n')[0].strip() if docstring else "No description available"
                
                # Get base classes
                bases = [ast.unparse(base) if hasattr(ast, 'unparse') else base.id if isinstance(base, ast.Name) else str(base) for base in node.bases]
                
                classes.append({
                    'name': node.name,
                    'description': description,
                    'bases': bases
                })
    except Exception as e:
        # If parsing fails, return empty list
        pass
    
    return classes

def scan_directory(root_dir: Path) -> Dict[str, Any]:
    """Scan directory and build structure summary"""
    structure = {}
    
    # Get all Python files
    python_files = sorted(root_dir.rglob('*.py'))
    
    for py_file in python_files:
        # Skip __pycache__ and venv
        if '__pycache__' in str(py_file) or 'venv' in str(py_file):
            continue
        
        # Get relative path
        rel_path = py_file.relative_to(root_dir)
        file_key = str(rel_path).replace('\\', '/')
        
        # Extract classes
        classes = extract_classes_from_file(py_file)
        
        if classes:
            structure[file_key] = {
                'filepath': file_key,
                'classes': classes
            }
        else:
            # Include file even if no classes (might have functions, etc.)
            structure[file_key] = {
                'filepath': file_key,
                'classes': []
            }
    
    return structure

def filter_structure_by_module(structure: Dict[str, Any], module_name: str) -> Dict[str, Any]:
    """Filter structure to only include files from a specific module across all layers"""
    filtered = {}
    
    # Define the layer paths where modules can exist
    layer_paths = [
        f'app/data/{module_name}',
        f'app/buisness/{module_name}',
        f'app/services/{module_name}',
        f'app/presentation/routes/{module_name}',
        f'app/presentation/templates/{module_name}',
        f'app/presentation/static/{module_name}',
    ]
    
    for filepath, data in structure.items():
        # Check if filepath starts with any of the layer paths
        if any(filepath.startswith(layer_path) for layer_path in layer_paths):
            filtered[filepath] = data
    
    return filtered

def build_tree_structure(structure: Dict[str, Any], root_name: str = "module") -> List[str]:
    """Build a visual tree structure from the file paths"""
    if not structure:
        return [f"{root_name}/", "  (No files found)"]
    
    # Build a nested directory structure
    tree: Dict[str, Any] = {}
    
    for filepath in sorted(structure.keys()):
        parts = Path(filepath).parts
        current = tree
        for part in parts:
            if part not in current:
                current[part] = {}
            current = current[part]
    
    # Convert to tree lines
    lines = [f"{root_name}/"]
    
    def add_tree_lines(node: Dict, prefix: str = "", is_last_list: List[bool] = None):
        if is_last_list is None:
            is_last_list = []
        
        items = sorted(node.items())
        for i, (name, children) in enumerate(items):
            is_last = (i == len(items) - 1)
            
            # Determine the connector
            connector = "├── " if not is_last else "└── "
            extension = "│   " if not is_last else "    "
            
            # Add directory or file marker
            if children:
                lines.append(f"{prefix}{connector}{name}/")
                # Recursively add children
                new_prefix = prefix + extension
                add_tree_lines(children, new_prefix, is_last_list + [is_last])
            else:
                lines.append(f"{prefix}{connector}{name}")
    
    add_tree_lines(tree)
    return lines

def generate_module_document(structure: Dict[str, Any], module_name: str, output_path: Path):
    """Generate a combined structure and class description document for a module"""
    with open(output_path, 'w', encoding='utf-8') as f:
        # Header
        f.write(f"# {module_name.title()} Module Structure\n\n")
        f.write(f"This document provides an overview of the {module_name} module across all application layers.\n\n")
        
        # Module overview section
        f.write("## Module Layers\n\n")
        f.write("This module spans the following layers:\n\n")
        f.write(f"- **Data Layer**: `app/data/{module_name}/`\n")
        f.write(f"- **Business Layer**: `app/buisness/{module_name}/`\n")
        f.write(f"- **Services Layer**: `app/services/{module_name}/`\n")
        f.write(f"- **Presentation Layer**: `app/presentation/routes/{module_name}/`, `app/presentation/templates/{module_name}/`, `app/presentation/static/{module_name}/`\n\n")
        
        # Tree structure
        f.write("## File Structure\n\n")
        f.write("```\n")
        tree_lines = build_tree_structure(structure, module_name)
        for line in tree_lines:
            f.write(line + "\n")
        f.write("```\n\n")
        
        # Class descriptions
        f.write("## Class Descriptions\n\n")
        
        # Group by directory
        by_dir: Dict[str, List[Dict]] = {}
        for filepath, data in structure.items():
            dir_path = str(Path(filepath).parent)
            if dir_path not in by_dir:
                by_dir[dir_path] = []
            by_dir[dir_path].append(data)
        
        # Sort directories
        has_classes = False
        for dir_path in sorted(by_dir.keys()):
            # First check if this directory has any files with classes
            files_with_classes = [fd for fd in by_dir[dir_path] if fd['classes']]
            if not files_with_classes:
                continue  # Skip directories with no classes
            
            has_classes = True
            f.write(f"### {dir_path}\n\n")
            for file_data in sorted(by_dir[dir_path], key=lambda x: x['filepath']):
                # Only output files that have classes defined
                if file_data['classes']:
                    f.write(f"**{file_data['filepath']}**\n\n")
                    for cls in file_data['classes']:
                        bases_str = f" ({', '.join(cls['bases'])})" if cls['bases'] else ""
                        f.write(f"- **{cls['name']}**{bases_str}: {cls['description']}\n")
                    f.write("\n")
        
        if not has_classes:
            f.write("*No classes defined in this module.*\n")

def main():
    root_dir = Path('/home/cjb/asset_management')
    design_dir = root_dir / 'Design' / 'modules'
    design_dir.mkdir(exist_ok=True, parents=True)
    
    # Scan entire codebase
    print("Scanning application structure...")
    structure = scan_directory(root_dir)
    
    # Define modules to extract
    modules = ['assets', 'core', 'dispatching', 'inventory', 'maintenance']
    
    print(f"\nGenerating module-specific documents...\n")
    
    for module in modules:
        # Filter structure for this module
        module_structure = filter_structure_by_module(structure, module)
        
        # Generate document
        output_file = design_dir / f'{module}_structure.md'
        generate_module_document(module_structure, module, output_file)
        
        print(f"  ✓ {module}_structure.md ({len(module_structure)} files)")
    
    print(f"\nModule structure documents saved to: {design_dir}")
    print(f"Total modules processed: {len(modules)}")

if __name__ == '__main__':
    main()
