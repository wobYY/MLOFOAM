import atexit
import logging
import subprocess
import uuid

from ..conf import TEMP_DIR


class ContainerEngineManager:
    __PODMAN_EXISTS = (
        subprocess.run("podman --version", shell=True, capture_output=True).stderr
        == b""
    )
    DOCKER_EXISTS = (
        subprocess.run("docker --version", shell=True, capture_output=True).stderr
        == b""
    )
    __INSTANCE = None

    def __new__(cls, *args, **kwargs):
        if cls.__INSTANCE is None:
            cls.__INSTANCE = super(ContainerEngineManager, cls).__new__(cls)
        return cls.__INSTANCE

    def __init__(self, preferred_engine: str | None = None):
        # TODO: add docstrings
        self.engine = self.get_container_engine(preferred_engine=preferred_engine)

    @classmethod
    def get_container_engine(cls, preferred_engine: str | None = None) -> str:
        # TODO: Add docstrings
        if isinstance(preferred_engine, str):
            preferred_engine = preferred_engine.lower()

        if (
            preferred_engine == "podman" or preferred_engine is None
        ) and cls.__PODMAN_EXISTS:
            return "podman"
        elif (
            preferred_engine == "docker" or preferred_engine is None
        ) and cls.DOCKER_EXISTS:
            return "docker"
        else:
            err_msg = (
                "Neither Podman nor Docker"
                if preferred_engine is None
                else f"Preferred engine '{preferred_engine}'"
            )
            raise RuntimeError(f"{err_msg} is installed on this system.")


class ContainerManager:
    def __init__(
        self,
        image_name: str,
        container_engine: ContainerEngineManager,
        ports: dict[int, str | int] | None = None,
        volume_mounts: dict[str, str] | None = None,
        additional_runtime_args: str = "",
        remove_image_on_exit: bool = False,
        remove_container_on_exit: bool = True,
    ):
        # TODO: Add docstrings
        self.container_engine = container_engine.engine
        self.image_name = image_name
        self.containers = set()

        self.ports = ports or {}
        self.volume_mounts = volume_mounts or {}
        self.additional_runtime_args = additional_runtime_args

        if remove_image_on_exit:
            # Remove the image atexit to avoid cluttering the system with unused images
            atexit.register(self.remove_image)
            logging.debug(
                "Registed image removal on exit for image: %s",
                self.image_name,
            )

    def __generate_container_name(self) -> str:
        # TODO: Add docstrings
        while True:
            container_name = f"mlofoam_{uuid.uuid4().hex[:12]}"

            if container_name not in self.containers:
                self.containers.add(container_name)
                return container_name

    def pull_image(self) -> None:
        # TODO: Add docstrings
        logging.info(
            "Pulling image '%s' using %s...",
            self.image_name,
            self.container_engine,
        )
        subprocess.run(
            f"{self.container_engine} image pull {self.image_name}",
            shell=True,
            check=True,
        )

    def remove_image(self) -> None:
        # TODO: Add docstrings
        logging.info(
            "Removing image '%s' using %s...",
            self.image_name,
            self.container_engine,
        )
        subprocess.run(
            f"{self.container_engine} image rm {self.image_name}",
            shell=True,
            check=True,
        )

    def create_container(self, command: str = "") -> str:
        # TODO: Add docstrings
        container_name = self.__generate_container_name()

        port_flags = " ".join(
            f"-p {host_port}:{container_port}"
            for host_port, container_port in self.ports.items()
        )

        for volume_mount_dir in self.volume_mounts.keys():
            (TEMP_DIR / container_name / volume_mount_dir).mkdir(
                parents=True, exist_ok=True
            )

        volume_mount_flags = " ".join(
            f"-v {TEMP_DIR / container_name / host_dir}:{container_dir}"
            for host_dir, container_dir in self.volume_mounts.items()
        )

        # Make sure that the command doesn't contain args we ask the user to
        # specify via the constructor
        if "-p " in command or "--publish " in command:
            raise ValueError(
                "Port mappings should be specified using the 'ports' argument of the ContainerManager constructor, not in the command string."
            )

        if "-v " in command or "--volume " in command:
            raise ValueError(
                "Volume mounts should be specified using the 'volume_mounts' argument of the ContainerManager constructor, not in the command string."
            )

        logging.info(
            "Creating container '%s' using %s...",
            container_name,
            self.container_engine,
        )
        subprocess.run(
            f"{self.container_engine} run -d --name {container_name} \
                {volume_mount_flags} {port_flags} \
                {self.additional_runtime_args} {self.image_name} {command}",
            shell=True,
            check=True,
        )

        # Add the container name to the set of managed containers
        self.containers.add(container_name)
        return container_name

    def remove_container(self, container_name: str) -> None:
        # TODO: Add docstrings
        logging.info(
            "Removing container '%s' using %s...",
            container_name,
            self.container_engine,
        )
        subprocess.run(
            f"{self.container_engine} rm -f {container_name}",
            shell=True,
            check=True,
        )
        self.containers.discard(container_name)

    def exec_in_container(self, container_name: str, command: str) -> None:
        # TODO: Add docstrings
        logging.debug(
            "Executing shell command '%s' in container '%s' using %s...",
            command,
            container_name,
            self.container_engine,
        )
        subprocess.run(
            f"{self.container_engine} exec {container_name} {command}",
            shell=True,
            check=True,
        )
