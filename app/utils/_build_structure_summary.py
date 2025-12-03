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

def main():
    root_dir = Path('/home/cjb/asset_management')
    structure = scan_directory(root_dir)
    
    # Save as JSON
    design_dir = root_dir / 'Design'
    design_dir.mkdir(exist_ok=True)
    output_json = design_dir / 'application_structure.json'
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(structure, f, indent=2, ensure_ascii=False)
    
    # Also create markdown version
    output_md = design_dir / 'application_structure.md'
    with open(output_md, 'w', encoding='utf-8') as f:
        f.write("# Application Structure Summary\n\n")
        f.write("This document provides a comprehensive overview of all files and classes in the application.\n\n")
        
        # Group by directory
        by_dir: Dict[str, List[Dict]] = {}
        for filepath, data in structure.items():
            dir_path = str(Path(filepath).parent)
            if dir_path not in by_dir:
                by_dir[dir_path] = []
            by_dir[dir_path].append(data)
        
        # Sort directories
        for dir_path in sorted(by_dir.keys()):
            f.write(f"## {dir_path or 'Root'}\n\n")
            for file_data in sorted(by_dir[dir_path], key=lambda x: x['filepath']):
                f.write(f"### {file_data['filepath']}\n\n")
                if file_data['classes']:
                    for cls in file_data['classes']:
                        bases_str = f" ({', '.join(cls['bases'])})" if cls['bases'] else ""
                        f.write(f"- **{cls['name']}**{bases_str}: {cls['description']}\n")
                else:
                    f.write("- *No classes defined*\n")
                f.write("\n")
    
    print(f"Structure summary saved to:")
    print(f"  - {output_json}")
    print(f"  - {output_md}")
    print(f"\nTotal files scanned: {len(structure)}")

if __name__ == '__main__':
    main()

