import io
import os
import random
import threading
import time
from datetime import datetime

import boto3
import dropbox
import dropbox.files as files
import psutil
import xmltodict
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.http import HttpResponse, HttpResponseRedirect
from django.template import loader
from dropbox import DropboxOAuth2Flow
from dropbox.exceptions import AuthError

from .forms import SignInForm, SignUpForm, CredentialForm, MachineForm
from .models import ExternalAccountCredentials, MachinePool, Machine


def index(request):
    if request.method == "POST":
        form = SignInForm(request.POST)
        if form.is_valid():
            entered_usr = request.POST.get("user_name")
            entered_pwd = request.POST.get("user_password")
            user = authenticate(username=entered_usr, password=entered_pwd)
            if user is not None:
                login(request, user)
                return HttpResponseRedirect("/user-home")
            else:
                return HttpResponseRedirect("/")
    else:
        form = SignInForm()

    template = loader.get_template("gcc/index.html")
    context = {"form": form}
    return HttpResponse(template.render(context, request))


def signup(request):
    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            usr = request.POST.get("user_name")
            pwd = request.POST.get("_user_password_")
            email = request.POST.get("user_email")
            try:
                user = User.objects.create_user(username=usr, password=pwd, email=email)
                login(request, user)

                mp = MachinePool()
                mp.user = user
                mp.save()

                ac = ExternalAccountCredentials()
                ac.user = user
                ac.aws_access_key = ""
                ac.aws_secret_access_key = ""
                ac.drbx_refresh_token = ""

                ac.save()

                return HttpResponseRedirect("/user-home")

            except Exception as e:
                print(e)
                return HttpResponseRedirect("/signup-error")
    else:
        form = SignUpForm()

    template = loader.get_template("gcc/signup.html")
    context = {
        "form": form,
    }
    return HttpResponse(template.render(context, request))


def signup_error(request):
    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            usr = request.POST.get("user_name")
            pwd = request.POST.get("_user_password_")
            email = request.POST.get("user_email")
            try:
                user = User.objects.create_user(username=usr, password=pwd, email=email)
                login(request, user)

                mp = MachinePool
                mp.user = user
                mp.save()

                ac = ExternalAccountCredentials()
                ac.user = user
                ac.aws_access_key = ""
                ac.aws_secret_access_key = ""
                ac.drbx_refresh_token = ""

                ac.save()

                return HttpResponseRedirect("/user-home")

            except Exception as e:
                print(e)
                return HttpResponseRedirect("/signup-error")
    else:
        form = SignUpForm()

    template = loader.get_template("gcc/signup_error.html")
    context = {
        "form": form,
    }
    return HttpResponse(template.render(context, request))


def user_logout(request):
    logout(request)
    return HttpResponseRedirect("/")


def user_home(request):
    template = loader.get_template("gcc/user_home.html")
    context = {
        "user": request.user,
        "datetime": datetime.now(),
    }
    return HttpResponse(template.render(context, request))


def user_workflows(request):
    workflows = {}
    aws_access_key = ExternalAccountCredentials.objects.filter(user=request.user)[
        0
    ].aws_access_key
    aws_secret_access_key = ExternalAccountCredentials.objects.filter(
        user=request.user
    )[0].aws_secret_access_key
    drbx_refresh_token = ExternalAccountCredentials.objects.filter(user=request.user)[
        0
    ].drbx_refresh_token

    try:
        dropbox.Dropbox(
            oauth2_refresh_token=drbx_refresh_token,
            app_key=os.environ.get("DRBX_APP_KEY"),
            app_secret=os.environ.get("DRBX_APP_SECRET"),
        ).check_user()
    except Exception:
        ExternalAccountCredentials.objects.filter(user=request.user).update(
            drbx_refresh_token=""
        )
        return HttpResponseRedirect("/user-credentials")

    try:
        boto3.client(
            "sts",
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_access_key,
        ).get_caller_identity()
    except Exception:
        ExternalAccountCredentials.objects.filter(user=request.user).update(
            aws_access_key=""
        )
        ExternalAccountCredentials.objects.filter(user=request.user).update(
            aws_secret_access_key=""
        )
        return HttpResponseRedirect("/user-credentials")

    if aws_access_key == "" or aws_secret_access_key == "" or drbx_refresh_token == "":
        return HttpResponseRedirect("/user-credentials")

    drbx = dropbox.Dropbox(
        oauth2_refresh_token=drbx_refresh_token,
        app_key=os.environ.get("DRBX_APP_KEY"),
        app_secret=os.environ.get("DRBX_APP_SECRET"),
    )

    dropbox_workflows = [
        item.name
        for item in drbx.files_list_folder("").entries
        if type(item) is files.FolderMetadata
    ]

    for workflow in dropbox_workflows:
        workflows[workflow] = {}
        try:
            workflows[workflow]["node_ct"] = len(
                drbx.files_list_folder(f"/{workflow}/nodes").entries
            )
        except Exception:
            workflows[workflow]["node_ct"] = 0
        try:
            workflows[workflow]["exec_ct"] = len(
                drbx.files_list_folder(f"/{workflow}/exec").entries
            )
        except Exception:
            workflows[workflow]["exec_ct"] = 0

    template = loader.get_template("gcc/user_workflows.html")
    context = {"workflows": workflows, "validated": False}
    return HttpResponse(template.render(context, request))


def user_workflows_validated(request):
    workflows = {}
    aws_access_key = ExternalAccountCredentials.objects.filter(user=request.user)[
        0
    ].aws_access_key
    aws_secret_access_key = ExternalAccountCredentials.objects.filter(
        user=request.user
    )[0].aws_secret_access_key
    drbx_refresh_token = ExternalAccountCredentials.objects.filter(user=request.user)[
        0
    ].drbx_refresh_token

    try:
        dropbox.Dropbox(
            oauth2_refresh_token=drbx_refresh_token,
            app_key=os.environ.get("DRBX_APP_KEY"),
            app_secret=os.environ.get("DRBX_APP_SECRET"),
        ).check_user()
    except Exception:
        ExternalAccountCredentials.objects.filter(user=request.user).update(
            drbx_refresh_token=""
        )
        return HttpResponseRedirect("/user-credentials")

    try:
        boto3.client(
            "sts",
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_access_key,
        ).get_caller_identity()
    except Exception:
        ExternalAccountCredentials.objects.filter(user=request.user).update(
            aws_access_key=""
        )
        ExternalAccountCredentials.objects.filter(user=request.user).update(
            aws_secret_access_key=""
        )
        return HttpResponseRedirect("/user-credentials")

    if aws_access_key == "" or aws_secret_access_key == "" or drbx_refresh_token == "":
        return HttpResponseRedirect("/user-credentials")

    drbx = dropbox.Dropbox(
        oauth2_refresh_token=drbx_refresh_token,
        app_key=os.environ.get("DRBX_APP_KEY"),
        app_secret=os.environ.get("DRBX_APP_SECRET"),
    )

    dropbox_workflows = [
        item.name
        for item in drbx.files_list_folder("").entries
        if type(item) is files.FolderMetadata and validate_workflow(drbx, item.name)
    ]

    for workflow in dropbox_workflows:
        workflows[workflow] = {}
        workflows[workflow]["node_ct"] = len(
            drbx.files_list_folder(f"/{workflow}/nodes").entries
        )
        try:
            workflows[workflow]["exec_ct"] = len(
                drbx.files_list_folder(f"/{workflow}/exec").entries
            )
        except Exception:
            workflows[workflow]["exec_ct"] = 0

    template = loader.get_template("gcc/user_workflows.html")
    context = {"workflows": workflows, "validated": True}
    return HttpResponse(template.render(context, request))


def _execute_workflow_(request, workflow_name: str):
    machine_pool = MachinePool.objects.get(user=request.user)
    available_machines = [
        machine
        for machine in machine_pool.machines.all()
        if machine.status == "Available"
    ]

    aws_access_key = ExternalAccountCredentials.objects.filter(user=request.user)[
        0
    ].aws_access_key
    aws_secret_access_key = ExternalAccountCredentials.objects.filter(
        user=request.user
    )[0].aws_secret_access_key
    drbx_refresh_token = ExternalAccountCredentials.objects.filter(user=request.user)[
        0
    ].drbx_refresh_token

    from .exec import User, Workflow

    temp_dir = gen_string()
    os.mkdir(f"{os.getcwd()}/tmp/{temp_dir}")

    user = User.User(
        drbx_refresh_token,
        os.environ.get("DRBX_APP_KEY"),
        os.environ.get("DRBX_APP_SECRET"),
        aws_access_key,
        aws_secret_access_key,
    )

    workflow = Workflow.Workflow(user, workflow_name, temp_dir)
    plan, used_machines = workflow.plan(available_machines)

    for machine in used_machines:
        machine_pool.machines.filter(id=machine.id).update(status="In use")

    workflow.initialize()
    workflow.configure(plan)
    profile_memory(workflow.execute, plan, workflow)
    workflow.complete()

    for machine in used_machines:
        machine_pool.machines.filter(id=machine.id).update(status="Available")


def elapsed_since(start):
    return time.strftime("%H:%M:%S", time.gmtime(time.time() - start))


def get_process_memory():
    process = psutil.Process(os.getpid())
    return process.memory_info().rss


def profile_memory(func, plan, workflow):
    mem_before = get_process_memory()
    start = time.time()
    func(plan)
    elapsed_time = elapsed_since(start)
    mem_after = get_process_memory()
    with open(f"{os.getcwd()}/tmp/{workflow.temp_dir}/stats.txt", "w+") as f:
        f.write(
            f"{func.__name__}:\n\tmemory before: {mem_before}\n\tmemory after: {mem_after}\n\tmemory consumed: {mem_after - mem_before}\n\texec time: {elapsed_time}"
        )
    workflow.drbx.upload_file(
        f"{os.getcwd()}/tmp/{workflow.temp_dir}/stats.txt",
        f"/{workflow.workflow_name}/exec/{workflow.exec_date_time}/stats.txt",
    )


def execute_workflow(request, workflow_name: str):
    t_exec = threading.Thread(target=_execute_workflow_, args=(request, workflow_name))
    t_exec.start()

    return HttpResponseRedirect("/user-workflows")


def user_dropbox_oauth(request):
    query_params = {"code": request.GET.get("code"), "state": request.GET.get("state")}

    oauth = DropboxOAuth2Flow(
        consumer_key=os.environ.get("DRBX_APP_KEY"),
        redirect_uri=os.environ.get("DRBX_REDIRECT_URI"),
        csrf_token_session_key="dropbox-auth-csrf-token",
        consumer_secret=os.environ.get("DRBX_APP_SECRET"),
        token_access_type="offline",
        session=request.session,
    )

    drbx_refresh_token = oauth.finish(query_params).refresh_token
    ExternalAccountCredentials.objects.filter(user=request.user).update(
        drbx_refresh_token=drbx_refresh_token
    )
    return HttpResponseRedirect("/user-credentials")


def user_machine_pool(request):
    machine_pool = MachinePool.objects.get(user=request.user)
    machines = machine_pool.machines.all()

    if request.method == "POST":
        form = MachineForm(request.POST)
        if form.is_valid():
            try:
                mac = Machine()
                mac.pool = machine_pool
                mac.id = request.POST.get("machine_id")
                mac.ip = request.POST.get("machine_ip")
                mac.pem = request.FILES["machine_pem"].read().decode("utf-8")
                mac.save()
            except Exception as e:
                print(e)
        return HttpResponseRedirect("/user-machine-pool")
    else:
        form = MachineForm()

    template = loader.get_template("gcc/machine_pool.html")
    context = {
        "machines": machines,
        "form": form,
    }
    return HttpResponse(template.render(context, request))


def user_machine_pool_delete(request, id):
    machine_pool = MachinePool.objects.get(user=request.user)
    machine_pool.machines.filter(id=id).delete()
    return HttpResponseRedirect("/user-machine-pool")


def user_credentials(request):
    oauth = DropboxOAuth2Flow(
        consumer_key=os.environ.get("DRBX_APP_KEY"),
        redirect_uri=os.environ.get("DRBX_REDIRECT_URI"),
        csrf_token_session_key="dropbox-auth-csrf-token",
        consumer_secret=os.environ.get("DRBX_APP_SECRET"),
        token_access_type="offline",
        session=request.session,
    )
    drbx_oauth_link = oauth.start()

    aws_access_key = ExternalAccountCredentials.objects.filter(user=request.user)[
        0
    ].aws_access_key
    aws_secret_access_key = ExternalAccountCredentials.objects.filter(
        user=request.user
    )[0].aws_secret_access_key
    drbx_refresh_token = ExternalAccountCredentials.objects.filter(user=request.user)[
        0
    ].drbx_refresh_token

    if drbx_refresh_token != "":
        try:
            dropbox.Dropbox(
                oauth2_refresh_token=drbx_refresh_token,
                app_key=os.environ.get("DRBX_APP_KEY"),
                app_secret=os.environ.get("DRBX_APP_SECRET"),
            ).check_user()
        except AuthError:
            ExternalAccountCredentials.objects.filter(user=request.user).update(
                drbx_refresh_token=""
            )

    if request.method == "POST":
        form = CredentialForm(request.POST)
        if form.is_valid():
            try:
                boto3.client(
                    "sts",
                    aws_access_key_id=request.POST.get("aws_access_key"),
                    aws_secret_access_key=request.POST.get("aws_secret_access_key"),
                ).get_caller_identity()
                ExternalAccountCredentials.objects.filter(user=request.user).update(
                    aws_access_key=request.POST.get("aws_access_key")
                )
                ExternalAccountCredentials.objects.filter(user=request.user).update(
                    aws_secret_access_key=request.POST.get("aws_secret_access_key")
                )
            except Exception:
                ExternalAccountCredentials.objects.filter(user=request.user).update(
                    aws_access_key=""
                )
                ExternalAccountCredentials.objects.filter(user=request.user).update(
                    aws_secret_access_key=""
                )

        return HttpResponseRedirect("/user-credentials")

    else:
        form = CredentialForm()
        form.fields["aws_access_key"].initial = aws_access_key
        form.fields["aws_secret_access_key"].initial = aws_secret_access_key

        if (
            ExternalAccountCredentials.objects.filter(user=request.user)[
                0
            ].aws_access_key
            == ""
            or ExternalAccountCredentials.objects.filter(user=request.user)[
                0
            ].aws_secret_access_key
            == ""
        ):
            aws_configured = None
        else:
            aws_configured = {
                "access_key": ExternalAccountCredentials.objects.filter(
                    user=request.user
                )[0].aws_access_key,
                "secret_key": ExternalAccountCredentials.objects.filter(
                    user=request.user
                )[0].aws_secret_access_key,
            }

        if (
            ExternalAccountCredentials.objects.filter(user=request.user)[
                0
            ].drbx_refresh_token
            == ""
        ):
            drbx_configured = None
        else:
            drbx_configured = ExternalAccountCredentials.objects.filter(
                user=request.user
            )[0].drbx_refresh_token

    template = loader.get_template("gcc/user_credentials.html")
    context = {
        "drbx_oauth_link": drbx_oauth_link,
        "drbx_configured": drbx_configured,
        "aws_configured": aws_configured,
        "user": request.user,
        "form": form,
    }
    return HttpResponse(template.render(context, request))


def validate_workflow(drbx, folder_to_validate_name: str):
    folder_to_validate_items = [
        item.name
        for item in drbx.files_list_folder(f"/{folder_to_validate_name}").entries
    ]

    if (
        "spec.xml" not in folder_to_validate_items
        or "nodes" not in folder_to_validate_items
    ):
        return False

    node_folder_items = [
        item.name
        for item in drbx.files_list_folder(f"/{folder_to_validate_name}/nodes").entries
    ]
    pem_folder_items = None

    if "pem" in folder_to_validate_items:
        pem_folder_items = [
            item.name
            for item in drbx.files_list_folder(
                f"/{folder_to_validate_name}/pem"
            ).entries
        ]

    for node in xmltodict.parse(
        get_file_contents(drbx, f"/{folder_to_validate_name}/spec.xml")
    )["workflow"]["task"]:
        if (
            pem_folder_items is not None
            and f"{node['vm']}" is not None
            and f"{node['vm']['@pem']}" is not None
            and f"{node['vm']['@pem']}" not in pem_folder_items
        ):
            return False

        if f"{node['@id']}.zip" not in node_folder_items:
            return False

    return True


def get_file_contents(drbx, drbx_file_path: str):
    _, result = drbx.files_download(drbx_file_path)
    with io.BytesIO(result.content) as stream:
        return stream.read().decode()


def get_file_link(drbx, drbx_file_path: str):
    result = drbx.files_get_temporary_link(drbx_file_path)
    return result.link


def gen_string():
    choices = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ-"
    return "".join([random.choice(choices) for _ in range(7)])
