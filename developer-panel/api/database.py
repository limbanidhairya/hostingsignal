"""Developer Panel Database Models & Connection"""
import socket
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text, JSON, ForeignKey, Enum as SAEnum, Uuid, select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from .config import get_settings

settings = get_settings()
if settings.DATABASE_URL.startswith("sqlite"):
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=settings.DEBUG,
        connect_args={"check_same_thread": False},
    )
else:
    engine = create_async_engine(settings.DATABASE_URL, echo=settings.DEBUG, pool_size=20, max_overflow=10)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()


async def get_db():
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()


# ─── Models ───────────────────────────────────────────────────────────

class DevAdmin(Base):
    __tablename__ = "dev_admins"
    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(100), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), default="admin")  # admin, viewer, operator
    is_active = Column(Boolean, default=True)
    last_login = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class ManagedServer(Base):
    __tablename__ = "managed_servers"
    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hostname = Column(String(255), nullable=False)
    ip_address = Column(String(45), nullable=False)
    port = Column(Integer, default=8000)
    status = Column(String(20), default="unknown")  # online, offline, degraded, unknown
    panel_version = Column(String(20), nullable=True)
    os_info = Column(String(100), nullable=True)
    cpu_cores = Column(Integer, nullable=True)
    ram_mb = Column(Integer, nullable=True)
    disk_gb = Column(Integer, nullable=True)
    cluster_id = Column(Uuid(as_uuid=True), ForeignKey("clusters.id"), nullable=True)
    last_heartbeat = Column(DateTime, nullable=True)
    license_key = Column(String(100), nullable=True)
    metadata_ = Column("metadata", JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    cluster = relationship("Cluster", back_populates="servers")
    metrics = relationship("ServerMetric", back_populates="server", cascade="all, delete-orphan")


class Cluster(Base):
    __tablename__ = "clusters"
    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    region = Column(String(50), nullable=True)
    status = Column(String(20), default="active")  # active, maintenance, degraded
    max_servers = Column(Integer, default=50)
    config = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    servers = relationship("ManagedServer", back_populates="cluster")


class PluginSubmission(Base):
    __tablename__ = "plugin_submissions"
    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    slug = Column(String(100), unique=True, nullable=False)
    version = Column(String(20), nullable=False)
    description = Column(Text, nullable=True)
    author = Column(String(100), nullable=False)
    author_email = Column(String(255), nullable=True)
    category = Column(String(50), default="utility")
    icon_url = Column(String(500), nullable=True)
    download_url = Column(String(500), nullable=True)
    file_hash = Column(String(128), nullable=True)
    file_size = Column(Integer, nullable=True)
    min_panel_version = Column(String(20), default="1.0.0")
    status = Column(String(20), default="pending")  # pending, approved, rejected, published
    review_notes = Column(Text, nullable=True)
    downloads = Column(Integer, default=0)
    rating = Column(Float, default=0.0)
    manifest = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PanelUpdate(Base):
    __tablename__ = "panel_updates"
    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    version = Column(String(20), unique=True, nullable=False)
    channel = Column(String(20), default="stable")  # stable, beta, nightly
    changelog = Column(Text, nullable=True)
    download_url = Column(String(500), nullable=True)
    file_hash = Column(String(128), nullable=True)
    file_size = Column(Integer, nullable=True)
    min_current_version = Column(String(20), nullable=True)
    is_critical = Column(Boolean, default=False)
    published = Column(Boolean, default=False)
    published_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class ServerMetric(Base):
    __tablename__ = "server_metrics"
    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    server_id = Column(Uuid(as_uuid=True), ForeignKey("managed_servers.id"), nullable=False)
    cpu_percent = Column(Float, nullable=True)
    ram_percent = Column(Float, nullable=True)
    disk_percent = Column(Float, nullable=True)
    network_in_mbps = Column(Float, nullable=True)
    network_out_mbps = Column(Float, nullable=True)
    load_average = Column(Float, nullable=True)
    active_connections = Column(Integer, nullable=True)
    uptime_seconds = Column(Integer, nullable=True)
    recorded_at = Column(DateTime, default=datetime.utcnow)
    server = relationship("ManagedServer", back_populates="metrics")


class AnalyticsEvent(Base):
    __tablename__ = "analytics_events"
    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type = Column(String(50), nullable=False)  # install, activate, deactivate, update, error
    server_id = Column(Uuid(as_uuid=True), nullable=True)
    license_key = Column(String(100), nullable=True)
    panel_version = Column(String(20), nullable=True)
    os_info = Column(String(100), nullable=True)
    metadata_ = Column("metadata", JSON, default=dict)
    ip_address = Column(String(45), nullable=True)
    country = Column(String(5), nullable=True)
    recorded_at = Column(DateTime, default=datetime.utcnow)


class AuditLog(Base):
    __tablename__ = "dev_audit_logs"
    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    admin_id = Column(Uuid(as_uuid=True), nullable=True)
    action = Column(String(100), nullable=False)
    resource_type = Column(String(50), nullable=True)
    resource_id = Column(String(100), nullable=True)
    details = Column(JSON, default=dict)
    ip_address = Column(String(45), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Ensure a deterministic default admin account for local/dev bootstrap.
    async with async_session() as session:
        from .auth import pwd_context

        admin_result = await session.execute(
            select(DevAdmin).where(DevAdmin.email == settings.DEFAULT_ADMIN_EMAIL).limit(1)
        )
        admin = admin_result.scalar_one_or_none()

        if admin is None:
            username_result = await session.execute(
                select(DevAdmin).where(DevAdmin.username == settings.DEFAULT_ADMIN_USERNAME).limit(1)
            )
            admin = username_result.scalar_one_or_none()

        if admin is None:
            admin = DevAdmin(
                username=settings.DEFAULT_ADMIN_USERNAME,
                email=settings.DEFAULT_ADMIN_EMAIL,
                password_hash=pwd_context.hash(settings.DEFAULT_ADMIN_PASSWORD),
                role="admin",
                is_active=True,
            )
            session.add(admin)
            await session.commit()
            return

        changed = False
        if admin.email != settings.DEFAULT_ADMIN_EMAIL:
            admin.email = settings.DEFAULT_ADMIN_EMAIL
            changed = True
        if admin.username != settings.DEFAULT_ADMIN_USERNAME:
            admin.username = settings.DEFAULT_ADMIN_USERNAME
            changed = True
        if not admin.is_active:
            admin.is_active = True
            changed = True
        if not pwd_context.verify(settings.DEFAULT_ADMIN_PASSWORD, admin.password_hash):
            admin.password_hash = pwd_context.hash(settings.DEFAULT_ADMIN_PASSWORD)
            changed = True

        if changed:
            await session.commit()

        if settings.AUTO_REGISTER_LOCAL_SERVER:
            await _ensure_local_managed_server(session)


async def _ensure_local_managed_server(session: AsyncSession):
    hostname = (settings.LOCAL_SERVER_HOSTNAME or "backend").strip()
    address = (settings.LOCAL_SERVER_ADDRESS or hostname).strip()
    resolved_ip = address

    try:
        resolved_ip = socket.gethostbyname(address)
    except OSError:
        # Fall back to the configured address when DNS resolution is unavailable.
        resolved_ip = address

    metadata = {
        "region": settings.LOCAL_SERVER_REGION,
        "bootstrap": True,
        "address": address,
    }

    result = await session.execute(
        select(ManagedServer).where(ManagedServer.hostname == hostname).limit(1)
    )
    server = result.scalar_one_or_none()

    if server is None:
        server = ManagedServer(
            hostname=hostname,
            ip_address=resolved_ip,
            port=settings.LOCAL_SERVER_PORT,
            status="online",
            os_info=settings.LOCAL_SERVER_OS_INFO or None,
            license_key=settings.LOCAL_SERVER_LICENSE_KEY or None,
            last_heartbeat=datetime.utcnow(),
            metadata_=metadata,
        )
        session.add(server)
        await session.commit()
        return

    changed = False
    if server.ip_address != resolved_ip:
        server.ip_address = resolved_ip
        changed = True
    if server.port != settings.LOCAL_SERVER_PORT:
        server.port = settings.LOCAL_SERVER_PORT
        changed = True
    if server.status != "online":
        server.status = "online"
        changed = True
    if server.os_info != (settings.LOCAL_SERVER_OS_INFO or None):
        server.os_info = settings.LOCAL_SERVER_OS_INFO or None
        changed = True
    if server.license_key != (settings.LOCAL_SERVER_LICENSE_KEY or None):
        server.license_key = settings.LOCAL_SERVER_LICENSE_KEY or None
        changed = True
    if (server.metadata_ or {}) != metadata:
        server.metadata_ = metadata
        changed = True

    server.last_heartbeat = datetime.utcnow()
    changed = True

    if changed:
        await session.commit()


async def _first_admin_id(session: AsyncSession):
    result = await session.execute(DevAdmin.__table__.select().with_only_columns(DevAdmin.id).limit(1))
    return result.scalar_one_or_none()
