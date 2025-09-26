from wpp_api import wppapi
import pandas as pd

convidados_df = pd.read_csv('convidados.csv')

row_selector = input("Digite o nome do noivo/a para filtrar os convidados: ").strip()
message_file_selector = input("Digite o nome do arquivo que contém a mensagem a ser enviada: ").strip()

image_file = None
has_image = input("Possui imagem? S para sim, N para não").strip().lower()
if has_image == 's':
    image_file = input("Digite o caminho do arquivo de imagem: ").strip()

convidados_df = convidados_df[['NOIVO', 'NOME', 'SOBRENOMES', 'TELEFONE']]
convidados_df = convidados_df[convidados_df['NOIVO'] == row_selector]

message = ''
with open(message_file_selector, 'r') as file:
    message = file.read().strip()

print("Mensagem:")
print(message)
print("Convidados selecionados:")
print(convidados_df['NOME'].tolist())

input("Pressione Enter para continuar, 'Ctrl + C' para cancelar...")

sent = []
not_sent = []
for index, row in convidados_df.iterrows():
    name = row['NOME']
    surname = row['SOBRENOMES']
    phone = row['TELEFONE']
    
    if pd.isna(surname):
        surname = ''
    
    if pd.isna(phone):
        print(f"Telefone não encontrado para {name} {surname}.")
        not_sent.append((name, surname, "Sem telefone"))
        continue

    print(f"Nome: {name} {surname}, Telefone: {phone}")

    # deixa apenas os números no telefone
    phone = ''.join(filter(str.isdigit, str(phone)))

    if not wppapi.is_contact(phone):
        print(f"Telefone {phone} não é um contato válido.")
        not_sent.append((name, surname, "Não é contato"))
        continue

    if has_image and image_file:
        sent_successful = wppapi.send_image(phone, image_file, message)
    else:
        sent_successful = wppapi.send_message(phone, message)

    if sent_successful:
        print(f"Mensagem enviada para {name} {surname} ({phone})")
        sent.append((name, surname, phone))
    else:
        print(f"Falha ao enviar mensagem para {name} {surname} ({phone})")
        not_sent.append((name, phone, "Falha ao enviar mensagem"))

wppapi.wait_for_completion()

print("Mensagens enviadas:")
for row in sent:
    print(row)

print("Mensagens não enviadas:")
for row in not_sent:
    print(row)

print("Processamento concluído.")
