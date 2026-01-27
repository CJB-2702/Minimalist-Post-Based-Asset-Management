#!/usr/bin/env python3
"""
Script to build a comprehensive summary of the application structure
"""
import ast
import json
from pathlib import Path
from typing import Dict, List, Any

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

def build_tree_structure(structure: Dict[str, Any], root_name: str = "asset_management") -> List[str]:
    """Build a visual tree structure from the file paths"""
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
            if not is_last_list:
                # Root level
                connector = "├── " if not is_last else "└── "
                extension = "│   " if not is_last else "    "
            else:
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

def main():
    root_dir = Path('/home/cjb/asset_management')
    structure = scan_directory(root_dir)
    
    # Save as JSON
    design_dir = root_dir / 'Design'
    design_dir.mkdir(exist_ok=True)
    output_json = design_dir / 'application_structure.json'
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(structure, f, indent=2, ensure_ascii=False)
    
    # Create application_structure.md with tree structure
    output_structure_md = design_dir / 'application_structure.md'
    with open(output_structure_md, 'w', encoding='utf-8') as f:
        f.write("# Application Structure\n\n")
        f.write("""##run the following command to see condensed output\n grep -v "\.py" Design/application_structure.md""")
        f.write("This document provides a visual overview of the file structure in the application.\n\n")
        f.write("For detailed class descriptions, see [class_descriptions.md](class_descriptions.md).\n\n")
        
        f.write("## File Structure\n\n")
        f.write("```\n")
        tree_lines = build_tree_structure(structure, "asset_management")
        for line in tree_lines:
            f.write(line + "\n")
        f.write("```\n")
    
    # Create class_descriptions.md with detailed class information
    output_classes_md = design_dir / 'class_descriptions.md'
    with open(output_classes_md, 'w', encoding='utf-8') as f:
        f.write("# Class Descriptions\n\n")
        f.write("This document provides detailed information about all classes defined in the application.\n\n")
        f.write("For the file structure overview, see [application_structure.md](application_structure.md).\n\n")
        
        # Group by directory
        by_dir: Dict[str, List[Dict]] = {}
        for filepath, data in structure.items():
            dir_path = str(Path(filepath).parent)
            if dir_path not in by_dir:
                by_dir[dir_path] = []
            by_dir[dir_path].append(data)
        
        # Sort directories
        for dir_path in sorted(by_dir.keys()):
            # First check if this directory has any files with classes
            files_with_classes = [fd for fd in by_dir[dir_path] if fd['classes']]
            if not files_with_classes:
                continue  # Skip directories with no classes
            
            f.write(f"## {dir_path or 'Root'}\n\n")
            for file_data in sorted(by_dir[dir_path], key=lambda x: x['filepath']):
                # Only output files that have classes defined
                if file_data['classes']:
                    f.write(f"### {file_data['filepath']}\n\n")
                    for cls in file_data['classes']:
                        bases_str = f" ({', '.join(cls['bases'])})" if cls['bases'] else ""
                        f.write(f"- **{cls['name']}**{bases_str}: {cls['description']}\n")
                    f.write("\n")
    
    print(f"Structure summary saved to:")
    print(f"  - {output_json}")
    print(f"  - {output_structure_md}")
    print(f"  - {output_classes_md}")
    print(f"\nTotal files scanned: {len(structure)}")

if __name__ == '__main__':
    main()

