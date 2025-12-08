import streamlit as st
import mysql.connector
import pandas as pd
import datetime
import io # Para generar el Excel en memoria

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
        use_pure=True # Importante para evitar errores de librerías
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

# Función para asegurar que la tabla exista (por si cambias de base de datos)
def inicializar_bd():
    sql = """CREATE TABLE IF NOT EXISTS incidencias_v2 (
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
    run_query(sql)

inicializar_bd()

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
            usuario = st.text_input("Su Nombre / Empresa")
            obra = st.text_input("Obra / Sede")
        with col2:
            inventario = st.text_input("Nro de Inventario")
            prioridad = st.selectbox("Prioridad", ["Baja", "Normal", "Alta", "URGENTE"], index=1)
        
        asunto = st.text_input("Asunto Corto")
        descripcion = st.text_area("Descripción detallada del problema", height=100)
        
        # Botón de envío
        enviado = st.form_submit_button("🚀 ENVIAR REPORTE")
        
        if enviado:
            if not usuario or not obra or not inventario or not asunto or not descripcion:
                st.warning("⚠️ Por favor complete todos los campos obligatorios.")
            else:
                fecha = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                sql = """INSERT INTO incidencias_v2 
                         (fecha, usuario, obra, inventario, asunto, descripcion, prioridad, estado) 
                         VALUES (%s, %s, %s, %s, %s, %s, %s, 'Abierto')"""
                
                if run_query(sql, (fecha, usuario, obra, inventario, asunto, descripcion, prioridad)):
                    st.success("✅ ¡Incidencia registrada correctamente en la Nube!")
                    st.balloons()

# --- 5. PÁGINA: ADMINISTRADOR ---
elif menu == "🔒 Panel Administrador":
    st.title("🔒 Gestión de Tickets")
    
    # Login simple
    password = st.sidebar.text_input("Contraseña Admin", type="password")
    
    if password == "admin123": # <--- CLAVE DE ADMIN
        
        # --- A. MÉTRICAS (KPIs) ---
        conn = get_connection()
        df = pd.read_sql("SELECT * FROM incidencias_v2 ORDER BY id DESC", conn)
        conn.close()
        
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        kpi1.metric("Total Tickets", len(df))
        kpi2.metric("Abiertos", len(df[df['estado']=='Abierto']), delta_color="inverse")
        kpi3.metric("En Proceso", len(df[df['estado']=='En Proceso']), delta_color="off")
        kpi4.metric("Urgentes", len(df[df['prioridad']=='URGENTE']), delta_color="inverse")
        
        st.divider()
        
        # --- B. FILTROS Y TABLA ---
        col_filtro1, col_filtro2 = st.columns(2)
        with col_filtro1:
            filtro_estado = st.selectbox("Filtrar por Estado:", ["Todos", "Abierto", "En Proceso", "Cerrado"])
        
        if filtro_estado != "Todos":
            df_mostrar = df[df['estado'] == filtro_estado]
        else:
            df_mostrar = df
            
        st.dataframe(df_mostrar, use_container_width=True, hide_index=True)
        
        # --- C. ACCIONES (CAMBIAR ESTADO) ---
        st.subheader("🛠 Acciones Rápidas")
        col_accion1, col_accion2, col_accion3 = st.columns([1, 2, 1])
        
        with col_accion1:
            id_ticket = st.number_input("ID del Ticket", min_value=1, step=1)
        with col_accion2:
            nuevo_estado = st.selectbox("Nuevo Estado", ["Abierto", "En Proceso", "Cerrado"])
        with col_accion3:
            st.write("") # Espacio vacío para alinear
            st.write("") 
            if st.button("Actualizar Estado"):
                # Verificar si existe
                check = df[df['id'] == id_ticket]
                if not check.empty:
                    run_query("UPDATE incidencias_v2 SET estado = %s WHERE id = %s", (nuevo_estado, id_ticket))
                    st.success(f"Ticket #{id_ticket} actualizado a '{nuevo_estado}'")
                    st.rerun() # Recarga la página para ver cambios
                else:
                    st.error("ID no encontrado.")

        # --- D. EXPORTAR A EXCEL ---
        st.divider()
        st.subheader("📊 Reportes")
        
        # Convertir dataframe a Excel en memoria RAM (buffer)
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Reporte')
            
        st.download_button(
            label="📥 Descargar Excel Completo",
            data=buffer,
            file_name=f"Reporte_HelpDesk_{datetime.date.today()}.xlsx",
            mime="application/vnd.ms-excel"
        )
        
    else:
        if password:
            st.error("Contraseña incorrecta")
        st.info("Ingrese la contraseña en la barra lateral izquierda para acceder.")