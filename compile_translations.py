import os
import subprocess

def compile_translations():
    for lang in ['si', 'ta']:
        input_file = f'translations/{lang}/LC_MESSAGES/messages.po'
        output_file = f'translations/{lang}/LC_MESSAGES/messages.mo'

        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(output_file), exist_ok=True)

        # Use pybabel to compile the translations
        subprocess.run(['pybabel', 'compile', 
                      '-i', input_file,
                      '-o', output_file])

if __name__ == '__main__':
    compile_translations()