from flask_bcrypt import Bcrypt

# Generador de sentencias SQL compatibles con el nuevo esquema `sistemas`.
# Crea la fila en `adrecrear_usuarios` y luego inserta un permiso en
# `vta_permiso_usuarios` enlazado con `LAST_INSERT_ID()`.

bcrypt = Bcrypt()
usuarios = [
    ('CALC', 'supervisorCALC@recrear.cl', 'CALC', 'supervisor2025', 1, 1),
]

def _esc(s):
    return s.replace("'", "''") if isinstance(s, str) else s


for nombre, email, club, password, estado, permiso in usuarios:
    # Generar hash de la contraseña
    hash_pw = bcrypt.generate_password_hash(password).decode('utf-8')

    # INSERT para la nueva tabla `adrecrear_usuarios`
    insert_usuario = (
        "INSERT INTO `sistemas`.`adrecrear_usuarios` "
        "(nombre_usuario, email_usuario, clave_usuario, estado_usuario) VALUES ("
        "'%s', '%s', '%s', %d);" % (_esc(nombre), _esc(email), _esc(hash_pw), int(estado))
    )

    # INSERT para permisos: usamos LAST_INSERT_ID() para enlazar con el usuario creado
    insert_permiso = (
        "INSERT INTO `sistemas`.`vta_permiso_usuarios` "
        "(detalle_permiso, id_usuario_fk, vta_cajas_id_caja) VALUES ("
        "'%s', LAST_INSERT_ID(), %d);" % (_esc('perm_' + nombre), int(permiso))
    )

    # Imprimimos las sentencias en el orden correcto. Si se ejecutan en MySQL, LAST_INSERT_ID() apuntará al INSERT anterior.
    print(insert_usuario)
    print(insert_permiso)
