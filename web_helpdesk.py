import streamlit as st
import mysql.connector
import pandas as pd
import datetime
import io 

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

# Aseguramos que la tabla exista (con las nuevas columnas si es instalación nueva)
# --- BUSCA ESTA FUNCIÓN Y REEMPLAZALA POR ESTA VERSIÓN ---

def inicializar_bd():
    # 1. Crear tabla base si no existe (estructura original)
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

    # 2. PARCHE: Intentar agregar las columnas nuevas manualmente
    # Usamos try/except para que si ya existen, no se rompa el programa
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("ALTER TABLE incidencias_v2 ADD COLUMN comentarios TEXT")
        conn.commit()
        conn.close()
    except Exception:
        pass # Si falla, asumimos que la columna ya existe

    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("ALTER TABLE incidencias_v2 ADD COLUMN fecha_cierre DATETIME")
        conn.commit()
        conn.close()
    except Exception:
        pass # Si falla, asumimos que la columna ya existe

# --- 3. BARRA LATERAL (NAVEGACIÓN) ---
st.sidebar.image("https://cdn-icons-png.flaticon.com/512/6821/6821002.png", width=100)
st.sidebar.title("Navegación")
menu = st.sidebar.radio("Ir a:", ["📝 Reportar Incidencia", "🔒 Panel Administrador"])

# --- 4. PÁGINA: REPORTAR INCIDENCIA (USUARIO) ---
if menu == "📝 Reportar Incidencia":
    st.title("📝 Reportar Nueva Incidencia")
    st.markdown("Complete el formulario para enviar su solicitud al equipo de soporte.")

    with st.form("formulario_ticket", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            usuario = st.text_input("Su Nombre Completo")
            obra = st.text_input("Obra / Sede")
        with col2:
            inventario = st.text_input("Cod de Inventario")
            prioridad = st.selectbox("Prioridad", ["Baja", "Normal", "Alta", "URGENTE"], index=1)
        
        asunto = st.text_input("Asunto Corto")
        descripcion = st.text_area("Descripción detallada del problema", height=100)
        
        enviado = st.form_submit_button("🚀 ENVIAR REPORTE")
        
        if enviado:
            if not usuario or not obra or not inventario or not asunto or not descripcion:
                st.warning("⚠️ Por favor complete todos los campos obligatorios.")
            else:
                fecha = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                # Insertamos solo los datos básicos, el resto queda NULL o Default
                sql = """INSERT INTO incidencias_v2 
                         (fecha, usuario, obra, inventario, asunto, descripcion, prioridad, estado) 
                         VALUES (%s, %s, %s, %s, %s, %s, %s, 'Abierto')"""
                
                if run_query(sql, (fecha, usuario, obra, inventario, asunto, descripcion, prioridad)):
                    st.success("✅ ¡Incidencia registrada correctamente en la Nube!")
                    st.balloons()

# --- 5. PÁGINA: ADMINISTRADOR ---
elif menu == "🔒 Panel Administrador":
    st.title("🔒 Gestión de Tickets")
    
    password = st.sidebar.text_input("Contraseña Admin", type="password")
    
    if password == "admin123": 
        if password == "admin123": 
        
        # --- BOTÓN DE REPARACIÓN DE EMERGENCIA ---
        with st.expander("🔧 HERRAMIENTAS DE BASE DE DATOS (Usar si faltan columnas)"):
            if st.button("Forzar Actualización de Columnas"):
                conn = get_connection()
                cursor = conn.cursor()
                errores = []
                
                # Intentar agregar 'comentarios'
                try:
                    cursor.execute("ALTER TABLE incidencias_v2 ADD COLUMN comentarios TEXT")
                    st.success("✅ Columna 'comentarios' creada exitosamente.")
                except Exception as e:
                    errores.append(f"Info 'comentarios': {e}")

                # Intentar agregar 'fecha_cierre'
                try:
                    cursor.execute("ALTER TABLE incidencias_v2 ADD COLUMN fecha_cierre DATETIME")
                    st.success("✅ Columna 'fecha_cierre' creada exitosamente.")
                except Exception as e:
                    errores.append(f"Info 'fecha_cierre': {e}")
                
                conn.commit()
                conn.close()
                
                if errores:
                    st.info("Resultado de la actualización: " + " | ".join(errores))
                else:
                    st.balloons()
                    st.rerun()
        
        # --- AQUÍ SIGUE TU CÓDIGO NORMAL (Cargar datos, Tabs, etc.) ---
        conn = get_connection()
        # ...
        
        # Cargar datos
        conn = get_connection()
        # Leemos todas las columnas nuevas también
        df = pd.read_sql("SELECT * FROM incidencias_v2 ORDER BY id DESC", conn)
        conn.close()

        # --- PESTAÑAS DE ADMINISTRACIÓN ---
        tab1, tab2, tab3 = st.tabs(["📊 Tablero y Reportes", "🛠 Atender Tickets", "✏️ Editar/Eliminar"])

        # === TAB 1: VISUALIZACIÓN ===
        with tab1:
            # KPIs
            kpi1, kpi2, kpi3, kpi4 = st.columns(4)
            kpi1.metric("Total Tickets", len(df))
            kpi2.metric("Abiertos", len(df[df['estado']=='Abierto']), delta_color="inverse")
            kpi3.metric("En Proceso", len(df[df['estado']=='En Proceso']), delta_color="off")
            kpi4.metric("Cerrados", len(df[df['estado']=='Cerrado']), delta_color="normal")

            st.divider()
            
            # Filtros
            col_filtro1, col_filtro2 = st.columns(2)
            with col_filtro1:
                filtro_estado = st.selectbox("Filtrar por Estado:", ["Todos", "Abierto", "En Proceso", "Cerrado"])
            
            df_mostrar = df if filtro_estado == "Todos" else df[df['estado'] == filtro_estado]
            
            # Mostramos la tabla con las nuevas columnas
            st.dataframe(df_mostrar, use_container_width=True, hide_index=True)

            # Exportar Excel
            st.divider()
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Reporte')
            st.download_button(
                label="📥 Descargar Excel Completo",
                data=buffer,
                file_name=f"Reporte_HelpDesk_{datetime.date.today()}.xlsx",
                mime="application/vnd.ms-excel"
            )

        # === TAB 2: ATENDER TICKETS (ESTADO Y COMENTARIOS) ===
        with tab2:
            st.subheader("Actualizar Estado del Ticket")
            col_a1, col_a2 = st.columns([1, 3])
            
            with col_a1:
                id_atender = st.number_input("ID del Ticket a atender:", min_value=1, step=1)
            
            # Buscamos el ticket seleccionado para mostrar info actual
            ticket_actual = df[df['id'] == id_atender]
            
            if not ticket_actual.empty:
                st.info(f"Ticket #{id_atender} - {ticket_actual.iloc[0]['asunto']} (Usuario: {ticket_actual.iloc[0]['usuario']})")
                
                with st.form("form_atencion"):
                    nuevo_estado = st.selectbox("Nuevo Estado", ["Abierto", "En Proceso", "Cerrado"], index=0)
                    # --- CÓDIGO NUEVO Y SEGURO (COPIA ESTO) ---
valor_comentario = ""
# Verificamos si la columna existe antes de intentar leerla
if 'comentarios' in df.columns:
    if ticket_actual.iloc[0]['comentarios']:
        valor_comentario = ticket_actual.iloc[0]['comentarios']

nuevo_comentario = st.text_area("Comentarios Técnicos / Detalle de atención", value=valor_comentario)
                    
                    btn_actualizar = st.form_submit_button("💾 Guardar Cambios")
                    
                    if btn_actualizar:
                        fecha_cierre_val = None
                        
                        # Lógica para fecha de cierre
                        if nuevo_estado == "Cerrado":
                            # Si ya tenía fecha, la mantenemos, si no, ponemos la actual
                            fecha_cierre_val = datetime.datetime.now()
                        
                        # SQL dinámico dependiendo si cerramos o no
                        if nuevo_estado == "Cerrado":
                            sql = "UPDATE incidencias_v2 SET estado=%s, comentarios=%s, fecha_cierre=%s WHERE id=%s"
                            params = (nuevo_estado, nuevo_comentario, fecha_cierre_val, id_atender)
                        else:
                            # Si lo reabrimos, podríamos querer limpiar la fecha de cierre o dejarla.
                            # Aquí actualizamos estado y comentario solamente
                            sql = "UPDATE incidencias_v2 SET estado=%s, comentarios=%s WHERE id=%s"
                            params = (nuevo_estado, nuevo_comentario, id_atender)
                            
                        run_query(sql, params)
                        st.success(f"Ticket #{id_atender} actualizado correctamente.")
                        st.rerun()
            else:
                st.warning("Ingrese un ID válido para ver detalles.")

        # === TAB 3: EDITAR O ELIMINAR (CORRECCIONES) ===
        with tab3:
            st.subheader("✏️ Corregir Datos o 🗑 Eliminar")
            
            col_e1, col_e2 = st.columns([1, 3])
            with col_e1:
                id_editar = st.number_input("ID del Ticket a editar/borrar:", min_value=1, step=1, key="edit_id")
            
            ticket_edit = df[df['id'] == id_editar]
            
            if not ticket_edit.empty:
                # Mostrar formulario precargado para editar
                with st.expander("✏️ Editar Información (Corregir errores)", expanded=True):
                    with st.form("form_edicion"):
                        e_usuario = st.text_input("Usuario", value=ticket_edit.iloc[0]['usuario'])
                        e_inventario = st.text_input("Inventario", value=ticket_edit.iloc[0]['inventario'])
                        e_obra = st.text_input("Obra", value=ticket_edit.iloc[0]['obra'])
                        e_descripcion = st.text_area("Descripción", value=ticket_edit.iloc[0]['descripcion'])
                        
                        if st.form_submit_button("Actualizar Datos"):
                            sql_edit = "UPDATE incidencias_v2 SET usuario=%s, inventario=%s, obra=%s, descripcion=%s WHERE id=%s"
                            run_query(sql_edit, (e_usuario, e_inventario, e_obra, e_descripcion, id_editar))
                            st.success("Datos corregidos.")
                            st.rerun()
                
                st.divider()
                
                # Zona de Peligro: Eliminar
                st.markdown("### 🚫 Zona de Peligro")
                col_del1, col_del2 = st.columns([3, 1])
                with col_del1:
                    st.warning(f"¿Estás seguro que deseas eliminar el ticket #{id_editar} permanentemente?")
                with col_del2:
                    if st.button("🗑 ELIMINAR TICKET", type="primary"):
                        run_query("DELETE FROM incidencias_v2 WHERE id=%s", (id_editar,))
                        st.error(f"Ticket #{id_editar} eliminado.")
                        st.rerun()

            else:
                st.info("Seleccione un ID existente.")

    else:
        if password:
            st.error("Contraseña incorrecta")
        st.info("Ingrese la contraseña en la barra lateral.")


