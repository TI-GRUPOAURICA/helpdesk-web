import streamlit as st
import mysql.connector
import pandas as pd
import datetime
import io 
import pytz 

# --- 1. CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title="HelpDesk Cloud",
    page_icon="🔧",
    layout="wide"
)

# --- 2. CONEXIÓN A LA NUBE (TiDB) ---
def get_connection():
    return mysql.connector.connect(
        host='gateway01.ap-northeast-1.prod.aws.tidbcloud.com',
        user='2JjrwpZkCSGKcia.root',
        password=st.secrets["db_password"],
        database='test',
        port=4000,
        ssl_disabled=False,
        use_pure=True 
    )

def run_query(query, params=()):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        if query.strip().upper().startswith("SELECT"):
            result = cursor.fetchall()
            conn.close()
            return result
        else:
            conn.commit()
            conn.close()
            return True
    except Exception as e:
        st.error(f"Error de base de datos: {e}")
        return None

def obtener_hora_peru():
    zona_peru = pytz.timezone('America/Lima')
    return datetime.datetime.now(zona_peru)

# --- INICIALIZACIÓN Y REPARACIÓN DE BD ---
def inicializar_bd():
    sql_create = """CREATE TABLE IF NOT EXISTS incidencias_v2 (
                id INT AUTO_INCREMENT PRIMARY KEY,
                fecha DATETIME,
                usuario VARCHAR(100),
                obra VARCHAR(100),
                inventario VARCHAR(50),
                asunto VARCHAR(150),
                descripcion TEXT,
                prioridad VARCHAR(20),
                estado VARCHAR(20) DEFAULT 'Abierto'
            )"""
    run_query(sql_create)

    # Verificar columnas faltantes (Quitamos email de la lista)
    columnas_nuevas = [
        ("comentarios", "TEXT"),
        ("fecha_cierre", "DATETIME"),
        ("tipo", "VARCHAR(50)")
    ]

    for col_nombre, col_tipo in columnas_nuevas:
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(f"ALTER TABLE incidencias_v2 ADD COLUMN {col_nombre} {col_tipo}")
            conn.commit()
            conn.close()
        except Exception:
            pass 

inicializar_bd()

# --- 3. BARRA LATERAL (NAVEGACIÓN) ---
st.sidebar.image("https://cdn-icons-png.flaticon.com/512/6821/6821002.png", width=100)
st.sidebar.title("Navegación")
menu = st.sidebar.radio("Ir a:", ["📝 Reportar Incidencia", "🔍 Rastrear Ticket", "🔒 Panel Administrador"])

# --- 4. PÁGINA: REPORTAR INCIDENCIA (USUARIO) ---
if menu == "📝 Reportar Incidencia":
    st.title("📝 Reportar Ticket")
    st.markdown("Seleccione el tipo de atención y complete el formulario.")

    tipo_seleccion = st.radio(
        "¿Qué tipo de atención requiere?",
        ["🛠 Soporte Técnico (Algo falla)", "📋 Solicitud"],
        horizontal=True
    )
    
    tipo_bd = "Soporte" if "Soporte" in tipo_seleccion else "Solicitud"

    st.divider()

    with st.form("formulario_ticket", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            usuario = st.text_input("Su Nombre Completo")
            obra = st.text_input("Obra / Sede")
        with col2:
            if tipo_bd == "Soporte":
                inventario = st.text_input("Cod de Inventario - MYJ-EI-XXX")
            else:
                st.info("🔹 Solicitud general (No requiere código de inventario)")
                inventario = "N/A - Solicitud"
            
        prioridad = st.selectbox("Prioridad", ["Baja", "Normal", "Alta", "URGENTE"], index=1)
        asunto = st.text_input("Asunto Corto")
        descripcion = st.text_area("Descripción detallada", height=100)
        
        enviado = st.form_submit_button("🚀 ENVIAR REPORTE")
        
        if enviado:
            if not usuario or not obra or not asunto or not descripcion:
                st.warning("⚠️ Por favor complete los campos obligatorios.")
            else:
                fecha = obtener_hora_peru().strftime("%Y-%m-%d %H:%M:%S")
                
                conn = get_connection()
                cursor = conn.cursor()
                # SQL SIN EMAIL
                sql = """INSERT INTO incidencias_v2 
                         (fecha, tipo, usuario, obra, inventario, asunto, descripcion, prioridad, estado) 
                         VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'Abierto')"""
                try:
                    cursor.execute(sql, (fecha, tipo_bd, usuario, obra, inventario, asunto, descripcion, prioridad))
                    conn.commit()
                    
                    # --- AQUÍ OBTENEMOS EL ID DEL TICKET ---
                    id_generado = cursor.lastrowid
                    conn.close()
                    
                    st.balloons()
                    st.success("✅ ¡Incidencia registrada correctamente!")
                    
                    # --- MENSAJE GIGANTE PARA EL USUARIO ---
                    st.markdown(f"""
                    <div style="background-color: #d1e7dd; color: #0f5132; padding: 20px; border-radius: 10px; border: 2px solid #badbcc; text-align: center; margin-top: 10px; margin-bottom: 20px;">
                        <h2 style="margin:0;">TICKET ID: {id_generado}</h2>
                        <p style="font-size: 18px; margin-top: 10px;">📸 <strong>Tome nota o capture este número</strong><br>lo necesitará para consultar el estado de su solicitud.</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                except Exception as e:
                    st.error(f"Error guardando ticket: {e}")
                    if conn.is_connected():
                        conn.close()

# --- 5. PÁGINA: RASTREAR TICKET ---
elif menu == "🔍 Rastrear Ticket":
    st.title("🔍 Estado de mi Solicitud")
    st.markdown("Ingrese su número de ticket para ver en qué estado se encuentra.")
    
    col_search1, col_search2 = st.columns([1, 2])
    with col_search1:
        id_busqueda = st.number_input("Ingrese ID del Ticket:", min_value=1, step=1, value=None)
        btn_buscar = st.button("Buscar")
        
    if btn_buscar and id_busqueda:
        conn = get_connection()
        try:
            df = pd.read_sql(f"SELECT * FROM incidencias_v2 WHERE id = {id_busqueda}", conn)
            conn.close()
            
            if not df.empty:
                ticket = df.iloc[0]
                estado = ticket['estado']
                
                color_estado = "blue"
                if estado == "Abierto": color_estado = "red"
                elif estado == "En Proceso": color_estado = "orange"
                elif estado == "Cerrado": color_estado = "green"
                
                st.markdown(f"### Estado: <span style='color:{color_estado}'>{estado}</span>", unsafe_allow_html=True)
                
                st.divider()
                c1, c2 = st.columns(2)
                c1.markdown(f"**📅 Fecha:** {ticket['fecha']}")
                c1.markdown(f"**👤 Usuario:** {ticket['usuario']}")
                c1.markdown(f"**📝 Asunto:** {ticket['asunto']}")
                
                tipo_t = ticket['tipo'] if 'tipo' in df.columns else "Soporte"
                c2.markdown(f"**📌 Tipo:** {tipo_t}")
                
                st.divider()
                st.markdown("#### 🔧 Respuesta Técnica / Comentarios:")
                
                coment = ticket['comentarios'] if 'comentarios' in df.columns and ticket['comentarios'] else "Su solicitud está en cola de atención."
                st.info(coment)
                
                if estado == "Cerrado" and 'fecha_cierre' in df.columns:
                    if ticket['fecha_cierre']:
                        st.success(f"🏁 Ticket cerrado el: {ticket['fecha_cierre']}")
                    
            else:
                st.error("❌ No encontramos ningún ticket con ese número. Verifique y reintente.")
        except Exception as e:
            st.error("Error buscando ticket. Intente nuevamente.")
            if conn.is_connected(): conn.close()

# --- 6. PÁGINA: ADMINISTRADOR ---
elif menu == "🔒 Panel Administrador":
    st.title("🔒 Gestión de Tickets")
    
    password = st.sidebar.text_input("Contraseña de Acceso", type="password")
    
    rol = None
    if password == "admin123": rol = "admin"
    elif password == "visita": rol = "invitado" 
    
    if rol:
        if rol == "admin":
            with st.expander("🔧 HERRAMIENTAS DE BASE DE DATOS"):
                if st.button("Verificar Columnas Nuevas"):
                    inicializar_bd()
                    st.success("✅ Verificación completada.")

        conn = get_connection()
        try:
            df = pd.read_sql("SELECT * FROM incidencias_v2 ORDER BY id DESC", conn)
        except Exception:
            df = pd.DataFrame()
        conn.close()

        if not df.empty:
            if rol == "invitado":
                st.info("👀 Modo Vista: Usted está viendo el estado de los tickets como invitado.")
                
                kpi1, kpi2, kpi3, kpi4 = st.columns(4)
                kpi1.metric("Total Tickets", len(df))
                abiertos = len(df[df['estado']=='Abierto']) if 'estado' in df.columns else 0
                proceso = len(df[df['estado']=='En Proceso']) if 'estado' in df.columns else 0
                cerrados = len(df[df['estado']=='Cerrado']) if 'estado' in df.columns else 0
                kpi2.metric("Abiertos", abiertos, delta_color="inverse")
                kpi3.metric("En Proceso", proceso, delta_color="off")
                kpi4.metric("Cerrados", cerrados, delta_color="normal")
                st.divider()
                
                col_filtro1, col_filtro2 = st.columns(2)
                with col_filtro1:
                    filtro_estado = st.selectbox("Filtrar por Estado:", ["Todos", "Abierto", "En Proceso", "Cerrado"])
                df_mostrar = df if filtro_estado == "Todos" else df[df['estado'] == filtro_estado]
                
                st.dataframe(df_mostrar, use_container_width=True, hide_index=True)
                
            elif rol == "admin":
                tab1, tab2, tab3 = st.tabs(["📊 Tablero Principal", "🛠 Atender Tickets", "✏️ Editar/Eliminar"])

                with tab1:
                    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
                    kpi1.metric("Total Tickets", len(df))
                    abiertos = len(df[df['estado']=='Abierto']) if 'estado' in df.columns else 0
                    proceso = len(df[df['estado']=='En Proceso']) if 'estado' in df.columns else 0
                    cerrados = len(df[df['estado']=='Cerrado']) if 'estado' in df.columns else 0
                    kpi2.metric("Abiertos", abiertos, delta_color="inverse")
                    kpi3.metric("En Proceso", proceso, delta_color="off")
                    kpi4.metric("Cerrados", cerrados, delta_color="normal")
                    st.divider()
                    
                    col_filtro1, col_filtro2 = st.columns(2)
                    with col_filtro1:
                        filtro_estado = st.selectbox("Filtrar por Estado:", ["Todos", "Abierto", "En Proceso", "Cerrado"])
                    df_mostrar = df if filtro_estado == "Todos" else df[df['estado'] == filtro_estado]
                    
                    st.dataframe(
                        df_mostrar,
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "id": st.column_config.NumberColumn("ID", format="%d", width="small"),
                            "fecha": st.column_config.DatetimeColumn("📅 Fecha", format="D/M/YY h:mm a"),
                            "tipo": st.column_config.TextColumn("📌 Tipo", width="small"),
                            "usuario": "Usuario",
                            "asunto": "Asunto",
                            "comentarios": st.column_config.TextColumn("🔧 Comentarios", width="medium"),
                            "fecha_cierre": st.column_config.DatetimeColumn("🏁 Cierre", format="D/M/YY h:mm a"),
                            "estado": st.column_config.TextColumn("Estado"),
                        }
                    )
                    st.divider()
                    buffer = io.BytesIO()
                    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                        df.to_excel(writer, index=False, sheet_name='Reporte')
                    st.download_button(label="📥 Descargar Excel", data=buffer, file_name=f"Reporte_{datetime.date.today()}.xlsx", mime="application/vnd.ms-excel")

                with tab2:
                    st.subheader("Actualizar Estado")
                    col_a1, col_a2 = st.columns([1, 3])
                    with col_a1:
                        id_atender = st.number_input("ID Ticket:", min_value=1, step=1)
                    ticket_actual = df[df['id'] == id_atender]
                    if not ticket_actual.empty:
                        tipo_t = ticket_actual.iloc[0]['tipo'] if 'tipo' in df.columns else "N/A"
                        st.info(f"Ticket #{id_atender} ({tipo_t}) - {ticket_actual.iloc[0]['asunto']}")
                        with st.form("form_atencion"):
                            estado_actual = ticket_actual.iloc[0]['estado']
                            opciones = ["Abierto", "En Proceso", "Cerrado"]
                            idx = opciones.index(estado_actual) if estado_actual in opciones else 0
                            nuevo_estado = st.selectbox("Nuevo Estado", opciones, index=idx)
                            valor_comentario = ""
                            if 'comentarios' in df.columns:
                                val = ticket_actual.iloc[0]['comentarios']
                                if val is not None and str(val).strip() != "":
                                    valor_comentario = str(val)
                            nuevo_comentario = st.text_area("Comentarios Técnicos", value=valor_comentario)
                            if st.form_submit_button("💾 Guardar Cambios"):
                                fecha_accion = obtener_hora_peru() if nuevo_estado == "Cerrado" else None
                                if 'fecha_cierre' in df.columns and 'comentarios' in df.columns:
                                    sql = "UPDATE incidencias_v2 SET estado=%s, comentarios=%s, fecha_cierre=%s WHERE id=%s"
                                    params = (nuevo_estado, nuevo_comentario, fecha_accion, id_atender)
                                    run_query(sql, params)
                                    st.success("✅ Actualizado correctamente.")
                                    st.rerun()
                    else:
                        st.warning("Ingrese un ID válido.")

                with tab3:
                    st.subheader("✏️ Editar / Borrar")
                    col_e1, col_e2 = st.columns([1, 3])
                    with col_e1:
                        id_editar = st.number_input("ID Ticket:", min_value=1, step=1, key="edit_id")
                    ticket_edit = df[df['id'] == id_editar]
                    if not ticket_edit.empty:
                        with st.expander("✏️ Editar Datos", expanded=True):
                            with st.form("form_edicion"):
                                tipo_actual = ticket_edit.iloc[0]['tipo'] if 'tipo' in df.columns else "Soporte"
                                opciones_tipo = ["Soporte", "Solicitud"]
                                idx_tipo = opciones_tipo.index(tipo_actual) if tipo_actual in opciones_tipo else 0
                                e_tipo = st.selectbox("Tipo", opciones_tipo, index=idx_tipo)
                                e_usuario = st.text_input("Usuario", value=ticket_edit.iloc[0]['usuario'])
                                e_inventario = st.text_input("Inventario", value=ticket_edit.iloc[0]['inventario'])
                                e_obra = st.text_input("Obra", value=ticket_edit.iloc[0]['obra'])
                                e_descripcion = st.text_area("Descripción", value=ticket_edit.iloc[0]['descripcion'])
                                if st.form_submit_button("Actualizar Datos"):
                                    if 'tipo' in df.columns:
                                        sql_edit = "UPDATE incidencias_v2 SET tipo=%s, usuario=%s, inventario=%s, obra=%s, descripcion=%s WHERE id=%s"
                                        params_edit = (e_tipo, e_usuario, e_inventario, e_obra, e_descripcion, id_editar)
                                    else:
                                        sql_edit = "UPDATE incidencias_v2 SET usuario=%s, inventario=%s, obra=%s, descripcion=%s WHERE id=%s"
                                        params_edit = (e_usuario, e_inventario, e_obra, e_descripcion, id_editar)
                                        
                                    run_query(sql_edit, params_edit)
                                    st.success("Datos corregidos.")
                                    st.rerun()
                        st.divider()
                        if st.button("🗑 ELIMINAR TICKET", type="primary"):
                            run_query("DELETE FROM incidencias_v2 WHERE id=%s", (id_editar,))
                            st.error("Ticket eliminado.")
                            st.rerun()
    else:
        if password:
            st.error("Contraseña incorrecta")
        st.info("Ingrese la contraseña en la barra lateral.")




