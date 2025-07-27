import os
import pdfplumber
from PIL import Image
import io
from dotenv import load_dotenv
import openai
import asyncio
from tkinter import Tk, filedialog
from tqdm import tqdm  # Importamos tqdm para la barra de progreso

# Cargar la clave API de OpenAI desde el archivo .env
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# Función para pedir al usuario que seleccione un archivo PDF
def pedir_archivo_pdf():
    root = Tk()
    root.withdraw()  # Oculta la ventana principal
    archivo = filedialog.askopenfilename(
        title="Selecciona un archivo PDF",
        filetypes=[("PDF files", "*.pdf")]
    )
    return archivo

# Función para describir imágenes usando GPT-4o-mini de forma asíncrona
async def describir_imagen(image_bytes):
    try:
        response = await openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Describe esta imagen como si estuvieras escribiendo un pie de foto detallado."}
            ],
            max_tokens=400
        )
        # Accedemos correctamente a los mensajes de la respuesta
        return response.choices[0].message['content'].strip()
    except Exception as e:
        return f"Error describiendo la imagen: {e}"

# Función para procesar el PDF y guardar texto e imágenes descritas en un archivo .txt
async def procesar_pdf(pdf_path, output_txt_path):
    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)  # Número total de páginas
        with open(output_txt_path, 'w', encoding='utf-8') as output_file:
            # Barra de progreso
            with tqdm(total=total_pages, desc="Procesando PDF") as pbar:
                for i, page in enumerate(pdf.pages):
                    # Extraer texto de la página
                    text = page.extract_text()
                    if text:
                        output_file.write(f"\n--- Página {i + 1}/{total_pages} ---\n")
                        output_file.write(text)
                        output_file.write("\n")

                    # Extraer imágenes de la página
                    for image in page.images:
                        x0, y0, x1, y1 = image["x0"], image["top"], image["x1"], image["bottom"]
                        # Obtener la imagen como objeto PIL.Image
                        img = page.to_image(resolution=300).original
                        cropped_img = img.crop((x0, y0, x1, y1))  # Aplicar crop correctamente con PIL

                        # Convertir la imagen recortada a bytes
                        img_bytes = io.BytesIO()
                        cropped_img.save(img_bytes, format="PNG")

                        # Describir la imagen usando IA
                        img_description = await describir_imagen(img_bytes.getvalue())
                        output_file.write(f"\n[Descripción de la imagen: {img_description}]\n")

                    # Actualizar la barra de progreso
                    pbar.update(1)

# Función principal
async def main():
    pdf_path = pedir_archivo_pdf()
    if not pdf_path:
        print("No se seleccionó ningún archivo PDF.")
        return
    
    output_txt_path = "resultado.txt"
    await procesar_pdf(pdf_path, output_txt_path)
    print(f"PDF procesado y guardado en {output_txt_path}")

# Ejecutar el programa
if __name__ == "__main__":
    asyncio.run(main())
